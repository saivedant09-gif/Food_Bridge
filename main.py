
from fastapi import FastAPI, HTTPException
from database import get_connection
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date
from mongodb import food_reviews
from datetime import datetime
from decimal import Decimal
from typing import Literal
import os
from fastapi.middleware.cors import CORSMiddleware
from query_api import router as query_router


app = FastAPI(
    title="Food Bridge API",
    description="Food Waste Management and Redistribution System",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)
app.include_router(query_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to Food Bridge API",
        "status": "running"
    }


@app.get("/food")
def get_food_listings():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                f.food_id,
                f.donor_id,
                f.food_name,
                f.quantity,
                f.available_quantity,
                f.unit,
                f.prepared_at,
                f.pickup_deadline,
                f.status,
                u.name AS donor_name,
                u.location
            FROM food_listings f
            JOIN users u
                ON f.donor_id = u.user_id
            ORDER BY f.food_id
        """)

        return cursor.fetchall()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve food listings"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

class FoodCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    donor_id: int = Field(gt=0)
    food_name: str = Field(min_length=2, max_length=150)
    quantity: float = Field(gt=0, le=1000000, multiple_of=0.01)
    unit: str = Field(min_length=1, max_length=30)
    prepared_at: datetime
    pickup_deadline: datetime

    @field_validator('prepared_at', 'pickup_deadline')
    @classmethod
    def local_datetime(cls, value):
        return value.astimezone().replace(tzinfo=None) if value.tzinfo else value


@app.post("/food", status_code=201)
def create_food(food: FoodCreate):
    connection = None
    cursor = None

    try:
        if food.pickup_deadline <= food.prepared_at:
            raise HTTPException(
                status_code=400,
                detail="Pickup deadline must be after preparation time"
            )

        if food.pickup_deadline <= datetime.now():
            raise HTTPException(400, 'Pickup deadline must be in the future')

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the donor exists and has the DONOR role
        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = %s AND role = %s",
            (food.donor_id, "DONOR")
        )

        donor = cursor.fetchone()

        if donor is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid donor ID or user is not a donor"
            )

        # Insert the new food listing
        cursor.execute(
            """
            INSERT INTO food_listings
            (donor_id, food_name, quantity, available_quantity,
             unit, prepared_at, pickup_deadline, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                food.donor_id,
                food.food_name,
                food.quantity,
                food.quantity,
                food.unit,
                food.prepared_at,
                food.pickup_deadline,
                "AVAILABLE"
            )
        )

        food_id = cursor.lastrowid
        connection.commit()

        return {
            "message": "Food listing created successfully",
            "food_id": food_id,
            "food_name": food.food_name,
            "quantity": food.quantity,
            "unit": food.unit,
            "status": "AVAILABLE"
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Error creating food listing:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to create food listing"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

class DonationRequestCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    food_id: int = Field(gt=0)
    ngo_id: int = Field(gt=0)
    requested_quantity: float = Field(gt=0, le=1000000, multiple_of=0.01)


@app.post("/requests", status_code=201)
def create_donation_request(request: DonationRequestCreate):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that the user exists and is an NGO
        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = %s AND role = %s",
            (request.ngo_id, "NGO")
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid NGO ID"
            )

        # Check the food listing and its availability
        cursor.execute(
            """
            SELECT food_id, available_quantity, status, pickup_deadline
            FROM food_listings
            WHERE food_id = %s
            """,
            (request.food_id,)
        )

        food = cursor.fetchone()

        if food is None:
            raise HTTPException(
                status_code=404,
                detail="Food listing not found"
            )

        if food["status"] != "AVAILABLE" or food['pickup_deadline'] <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Food listing is not available"
            )

        if request.requested_quantity > float(food["available_quantity"]):
            raise HTTPException(
                status_code=400,
                detail="Requested quantity exceeds available quantity"
            )

        # Create a pending request; approval happens separately
        cursor.execute(
            """
            INSERT INTO donation_requests
            (food_id, ngo_id, requested_quantity, status)
            VALUES (%s, %s, %s, %s)
            """,
            (
                request.food_id,
                request.ngo_id,
                request.requested_quantity,
                "PENDING"
            )
        )

        request_id = cursor.lastrowid
        connection.commit()

        return {
            "message": "Donation request created successfully",
            "request_id": request_id,
            "food_id": request.food_id,
            "ngo_id": request.ngo_id,
            "requested_quantity": request.requested_quantity,
            "status": "PENDING"
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Error creating donation request:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to create donation request"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

@app.put("/requests/{request_id}/approve")
def approve_request(request_id: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Lock the request row while processing approval
        cursor.execute(
            """
            SELECT request_id, food_id, requested_quantity, status
            FROM donation_requests
            WHERE request_id = %s
            FOR UPDATE
            """,
            (request_id,)
        )
        request = cursor.fetchone()

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Donation request not found"
            )

        if request["status"] != "PENDING":
            raise HTTPException(
                status_code=400,
                detail="Only pending requests can be approved"
            )

        # Lock the associated food listing
        cursor.execute(
            """
            SELECT available_quantity, status, pickup_deadline
            FROM food_listings
            WHERE food_id = %s
            FOR UPDATE
            """,
            (request["food_id"],)
        )
        food = cursor.fetchone()

        if food is None or food["status"] != "AVAILABLE" or food['pickup_deadline'] <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Food listing is not available"
            )

        requested = Decimal(str(request["requested_quantity"]))
        available = Decimal(str(food["available_quantity"]))

        if requested > available:
            raise HTTPException(
                status_code=400,
                detail="Insufficient available quantity"
            )

        remaining = available - requested

        # Deduct the approved quantity
        cursor.execute(
            """
            UPDATE food_listings
            SET available_quantity = %s,
                status = %s
            WHERE food_id = %s
            """,
            (
                remaining,
                "AVAILABLE" if remaining > 0 else "RESERVED",
                request["food_id"]
            )
        )

        cursor.execute(
            """
            UPDATE donation_requests
            SET status = 'APPROVED'
            WHERE request_id = %s
            """,
            (request_id,)
        )

        connection.commit()

        return {
            "message": "Donation request approved",
            "request_id": request_id,
            "approved_quantity": requested,
            "remaining_quantity": remaining,
            "status": "APPROVED"
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Approval error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to approve donation request"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()
@app.put("/requests/{request_id}/reject")
def reject_request(request_id: int):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE donation_requests
            SET status = 'REJECTED'
            WHERE request_id = %s
              AND status = 'PENDING'
            """,
            (request_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            raise HTTPException(
                status_code=400,
                detail="Request not found or is not pending"
            )

        connection.commit()

        return {
            "message": "Donation request rejected",
            "request_id": request_id,
            "status": "REJECTED"
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Rejection error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to reject request"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

class CollectionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    collected_quantity: float = Field(gt=0, le=1000000, multiple_of=0.01)
    notes: str = Field(default="", max_length=255)


@app.post("/requests/{request_id}/collect", status_code=201)
def collect_food(request_id: int, data: CollectionCreate):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Lock the request while processing collection
        cursor.execute(
            """
            SELECT request_id, food_id, requested_quantity, status
            FROM donation_requests
            WHERE request_id = %s
            FOR UPDATE
            """,
            (request_id,)
        )
        request = cursor.fetchone()

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Donation request not found"
            )

        if request["status"] != "APPROVED":
            raise HTTPException(
                status_code=400,
                detail="Only approved requests can be collected"
            )

        if data.collected_quantity > float(request["requested_quantity"]):
            raise HTTPException(
                status_code=400,
                detail="Collected quantity exceeds requested quantity"
            )

        # Keep the stock update in the same transaction as the collection.
        cursor.execute(
            'SELECT available_quantity, pickup_deadline, status FROM food_listings WHERE food_id = %s FOR UPDATE',
            (request['food_id'],)
        )
        food = cursor.fetchone()
        if food is None:
            raise HTTPException(404, 'Food listing not found')

        # Insert the collection record
        cursor.execute(
            """
            INSERT INTO collections
            (request_id, collected_quantity, notes)
            VALUES (%s, %s, %s)
            """,
            (
                request_id,
                data.collected_quantity,
                data.notes
            )
        )

        # Mark the request completed
        cursor.execute(
            """
            UPDATE donation_requests
            SET status = 'COMPLETED'
            WHERE request_id = %s
            """,
            (request_id,)
        )

        uncollected = Decimal(str(request['requested_quantity'])) - Decimal(str(data.collected_quantity))
        remaining = Decimal(str(food['available_quantity'])) + uncollected
        cursor.execute(
            "SELECT COUNT(*) AS pending_collections FROM donation_requests WHERE food_id = %s AND status = 'APPROVED'",
            (request['food_id'],)
        )
        pending_collections = cursor.fetchone()['pending_collections']
        if food['status'] in ('CANCELLED', 'EXPIRED'):
            food_status = food['status']
        elif food['pickup_deadline'] <= datetime.now():
            food_status = 'EXPIRED'
        elif remaining > 0:
            food_status = 'AVAILABLE'
        else:
            food_status = 'RESERVED' if pending_collections else 'COMPLETED'
        cursor.execute(
            'UPDATE food_listings SET available_quantity = %s, status = %s WHERE food_id = %s',
            (remaining, food_status, request['food_id'])
        )

        connection.commit()

        return {
            "message": "Food collection recorded successfully",
            "request_id": request_id,
            "collected_quantity": data.collected_quantity,
            "released_quantity": uncollected,
            "status": "COMPLETED"
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Collection error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to record collection"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

from mongodb import food_reviews

@app.get("/reviews")
def get_reviews():
    try:
        reviews = list(food_reviews.find({}, {"_id": 0}))
        return {
            "count": len(reviews),
            "reviews": reviews
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve reviews. Check the MongoDB connection."
        )

class FoodReviewCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    food_id: int = Field(gt=0)
    food_name: str = Field(min_length=2, max_length=150)
    reviewer_ngo: str = Field(min_length=1, max_length=150)
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(min_length=1, max_length=3000)
    quantity_received: float = Field(gt=0)
    review_date: date


@app.post("/reviews")
def create_review(review: FoodReviewCreate):
    try:
        review_data = review.model_dump(mode="json")

        
        result = food_reviews.insert_one(review_data)

        # Remove MongoDB's ObjectId before returning JSON
        review_data.pop("_id", None)

        return {
            "message": "Food review saved successfully",
            "review_id": str(result.inserted_id),
            "review": review_data
        }


    except Exception as error:
        print("POST /reviews error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Could not save review. Check the MongoDB connection."
        )


@app.get("/reviews/{food_id}")
def get_reviews_by_food(food_id: int):
    try:
        reviews = list(
            food_reviews.find(
                {"food_id": food_id},
                {"_id": 0}
            )
        )

        return {
            "food_id": food_id,
            "count": len(reviews),
            "reviews": reviews
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve food reviews. Check the MongoDB connection."
        )

