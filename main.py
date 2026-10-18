
from fastapi import FastAPI, HTTPException
from database import get_connection
from pydantic import BaseModel, Field
from datetime import date
from mongodb import food_reviews
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


app = FastAPI(
    title="Food Bridge API",
    description="Food Waste Management and Redistribution System",
    version="1.0"
)


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
                f.food_name,
                f.quantity,
                f.available_quantity,
                f.unit,
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
    donor_id: int = Field(gt=0)
    food_name: str = Field(min_length=2, max_length=150)
    quantity: float = Field(gt=0, le=1000000)
    unit: str = Field(min_length=1, max_length=30)
    prepared_at: datetime
    pickup_deadline: datetime


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
    food_id: int = Field(gt=0)
    ngo_id: int = Field(gt=0)
    requested_quantity: float = Field(gt=0, le=1000000)


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
            SELECT food_id, available_quantity, status
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

        if food["status"] != "AVAILABLE":
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
            SELECT available_quantity, status
            FROM food_listings
            WHERE food_id = %s
            FOR UPDATE
            """,
            (request["food_id"],)
        )
        food = cursor.fetchone()

        if food is None or food["status"] != "AVAILABLE":
            raise HTTPException(
                status_code=400,
                detail="Food listing is not available"
            )

        requested = float(request["requested_quantity"])
        available = float(food["available_quantity"])

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
    collected_quantity: float = Field(gt=0, le=1000000)
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

        connection.commit()

        return {
            "message": "Food collection recorded successfully",
            "request_id": request_id,
            "collected_quantity": data.collected_quantity,
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
            detail=f"Could not retrieve reviews: {str(error)}"
        )

class FoodReviewCreate(BaseModel):
    food_id: int = Field(gt=0)
    food_name: str
    reviewer_ngo: str
    rating: int = Field(ge=1, le=5)
    feedback: str
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
            detail=f"Could not save review: {str(error)}"
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
            detail=f"Could not retrieve food reviews: {str(error)}"
        )

