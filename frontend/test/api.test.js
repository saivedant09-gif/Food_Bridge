import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { api, API_BASE } from '../src/api.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
test('sends the real API path and JSON payload', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, `${API_BASE}/requests`);
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), {food_id:7, ngo_id:9, requested_quantity:2});
    assert.equal(options.headers['Content-Type'], 'application/json');
    return Response.json({request_id:12,status:'PENDING'}, {status:201});
  };
  assert.deepEqual(await api('/requests', {method:'POST',body:{food_id:7,ngo_id:9,requested_quantity:2}}), {request_id:12,status:'PENDING'});
});
test('surfaces FastAPI validation details', async () => {
  globalThis.fetch = async () => Response.json({detail:[{loc:['body','quantity'],msg:'Input should be greater than 0'}]}, {status:422});
  await assert.rejects(api('/food'), /quantity: Input should be greater than 0/);
});
test('surfaces business rule errors without inventing success', async () => {
  globalThis.fetch = async () => Response.json({detail:'Insufficient available quantity'}, {status:400});
  await assert.rejects(api('/requests/1/approve',{method:'PUT'}), /Insufficient available quantity/);
});
test('provides a useful error for offline servers', async () => {
  globalThis.fetch = async () => {throw new TypeError('fetch failed');};
  await assert.rejects(api('/food'), /Cannot reach the API/);
});
test('handles non JSON server errors', async () => {
  globalThis.fetch = async () => new Response('Bad gateway',{status:502});
  await assert.rejects(api('/food'), /Request failed \(502\)/);
});
