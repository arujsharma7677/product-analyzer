# 🚀 Product Analyzer API - Complete Documentation

**Base URL:** `http://127.0.0.1:8000` (Development)

---

## 📋 Table of Contents
1. [Authentication](#authentication)
2. [Auth Endpoints](#auth-endpoints)
3. [Credits Endpoints](#credits-endpoints)
4. [Product Analysis Endpoint](#product-analysis-endpoint)
5. [Error Codes](#error-codes)
6. [Integration Guide](#integration-guide)

---

## 🔐 Authentication

All endpoints (except signup/login) require a **JWT Bearer Token** obtained from the login endpoint.

### Token Storage (Frontend)
```javascript
// After successful login
const response = await fetch('http://127.0.0.1:8000/auth/login', {...});
const data = await response.json();
localStorage.setItem('jwt_token', data.access_token);
localStorage.setItem('user_id', data.user_id);
```

### Using Token in Requests
```javascript
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
  'Content-Type': 'application/json'
};
```

---

## 🔑 Auth Endpoints

### 1. Sign Up / Register
**Endpoint:** `POST /auth/signup`

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@company.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "seller_name": "JD Fashion Pvt Ltd",
    "country": "India",
    "address": "123 Market Street, Business Park",
    "pincode": "110001",
    "state": "Delhi",
    "gst": "18AABCG1234H1Z0"
  }'
```

**JavaScript/Fetch:**
```javascript
async function signup(userData) {
  const response = await fetch('http://127.0.0.1:8000/auth/signup', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
      seller_name: userData.sellerName,
      country: userData.country,
      address: userData.address,
      pincode: userData.pincode,
      state: userData.state,
      gst: userData.gst
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}
```

**Request Body:**
```json
{
  "email": "seller@company.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "seller_name": "JD Fashion Pvt Ltd",
  "country": "India",
  "address": "123 Market Street, Business Park",
  "pincode": "110001",
  "state": "Delhi",
  "gst": "18AABCG1234H1Z0"
}
```

**Success Response (200):**
```json
{
  "message": "Signup successful. Check your email to verify.",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "seller@company.com"
}
```

**Error Response (400):**
```json
{
  "detail": "Email address already registered"
}
```

---

### 2. Login
**Endpoint:** `POST /auth/login`

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@company.com",
    "password": "SecurePass123"
  }'
```

**JavaScript/Fetch:**
```javascript
async function login(email, password) {
  const response = await fetch('http://127.0.0.1:8000/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data = await response.json();
  
  // Store token
  localStorage.setItem('jwt_token', data.access_token);
  localStorage.setItem('user_id', data.user_id);
  localStorage.setItem('email', data.email);
  
  return data;
}
```

**Request Body:**
```json
{
  "email": "seller@company.com",
  "password": "SecurePass123"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxdXRlZ2V1empsYm9jYWhwenRiIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhdWQiOiJhdXRob3JpemVkIiwiaWF0IjoxNzc5OTY1MzAwLCJleHAiOjE3Nzk5NjU5MDB9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "seller@company.com"
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid email or password"
}
```

---

## 💳 Credits Endpoints

### 3. Get Credit Balance
**Endpoint:** `GET /api/credits`

**cURL:**
```bash
curl -X GET http://127.0.0.1:8000/api/credits \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**JavaScript/Fetch:**
```javascript
async function getCredits() {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch('http://127.0.0.1:8000/api/credits', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch credits');
  }
  
  return response.json();
}

// Usage
const creditData = await getCredits();
console.log(`Credits Remaining: ${creditData.credits_remaining}`);
console.log(`Total Used: ${creditData.credits_used}`);
```

**Success Response (200):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "credits_remaining": 25,
  "credits_used": 5,
  "total_credits": 30
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid or expired token"
}
```

---

### 4. Add Credits
**Endpoint:** `POST /api/credits/add`

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/credits/add \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 10
  }'
```

**JavaScript/Fetch:**
```javascript
async function addCredits(userId, amount) {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch('http://127.0.0.1:8000/api/credits/add', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      amount: amount
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// Usage
const result = await addCredits(userId, 10);
console.log(`New Balance: ${result.new_balance}`);
```

**Request Body:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 10
}
```

**Success Response (200):**
```json
{
  "message": "Credits added successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "credits_added": 10,
  "new_balance": 35
}
```

**Error Response:**
```json
{
  "detail": "User not found"
}
```

---

### 5. Get Usage History
**Endpoint:** `GET /api/credits/history`

**cURL:**
```bash
curl -X GET http://127.0.0.1:8000/api/credits/history \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**JavaScript/Fetch:**
```javascript
async function getUsageHistory() {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch('http://127.0.0.1:8000/api/credits/history', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch history');
  }
  
  return response.json();
}

// Usage
const history = await getUsageHistory();
history.forEach(entry => {
  console.log(`Date: ${entry.created_at}`);
  console.log(`Tokens: ${entry.input_tokens} input, ${entry.output_tokens} output`);
  console.log(`Cost: ₹${entry.cost_inr}`);
});
```

**Success Response (200):**
```json
[
  {
    "id": "uuid-1",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_tokens": 2500,
    "output_tokens": 1200,
    "cost_inr": 1.85,
    "credits_deducted": 1,
    "created_at": "2026-05-29T10:30:00Z"
  },
  {
    "id": "uuid-2",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_tokens": 2000,
    "output_tokens": 900,
    "cost_inr": 1.50,
    "credits_deducted": 1,
    "created_at": "2026-05-29T09:15:00Z"
  }
]
```

---

## 📸 Product Analysis Endpoint

### 6. Analyze Product Images
**Endpoint:** `POST /api/analyse`

**⚠️ Important:** 
- Maximum **5 images** per request
- Supported formats: JPEG, PNG, GIF, WebP
- Requires valid JWT token
- Deducts **1 credit** per analysis

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/analyse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "product_name=Nike Running Shoes" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "images=@image3.jpg"
```

**JavaScript/Fetch with FormData:**
```javascript
async function analyzeProduct(productName, imageFiles) {
  const token = localStorage.getItem('jwt_token');
  
  const formData = new FormData();
  formData.append('product_name', productName);
  
  // Add up to 5 images
  for (let i = 0; i < Math.min(imageFiles.length, 5); i++) {
    formData.append('images', imageFiles[i]);
  }
  
  const response = await fetch('http://127.0.0.1:8000/api/analyse', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// Usage
const files = [file1, file2, file3]; // FileList or File array
const result = await analyzeProduct('Nike Running Shoes', files);
console.log(result.analysis); // Product attributes
console.log(`Cost: ₹${result.cost_inr}`);
console.log(`Tokens Used - Input: ${result.input_tokens}, Output: ${result.output_tokens}`);
```

**React Example:**
```jsx
import { useState } from 'react';

export function ProductAnalyzer() {
  const [images, setImages] = useState([]);
  const [productName, setProductName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('jwt_token');
      const formData = new FormData();
      formData.append('product_name', productName);
      
      images.forEach(img => {
        formData.append('images', img);
      });

      const response = await fetch('http://127.0.0.1:8000/api/analyse', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const data = await response.json();
      setResult(data);
    } catch (err) {
      alert('Analysis failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Product Name"
        value={productName}
        onChange={(e) => setProductName(e.target.value)}
      />
      
      <input
        type="file"
        multiple
        accept="image/*"
        onChange={(e) => setImages(Array.from(e.target.files))}
      />
      
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze Product'}
      </button>

      {result && (
        <div>
          <h3>Analysis Results:</h3>
          <pre>{JSON.stringify(result.analysis, null, 2)}</pre>
          <p>Cost: ₹{result.cost_inr}</p>
          <p>Credits Used: {result.credits_deducted}</p>
        </div>
      )}
    </div>
  );
}
```

**Request:**
- `product_name` (form field, string, required)
- `images` (multipart files, max 5, required)

**Success Response (200):**
```json
{
  "analysis": {
    "articleType": "Shoes",
    "prominentColour": "BLACK",
    "secondProminentColour": "WHITE",
    "thirdProminentColour": "GREY",
    "brandColourRemarks": "BLACK AND WHITE",
    "topFabric": "Mesh",
    "bottomFabric": "Rubber",
    "topType": "Lace-up",
    "bottomType": "",
    "topPattern": "Solid",
    "bottomPattern": "",
    "sleeveLength": "",
    "neck": "",
    "occasion": "Sports",
    "fashionType": "Athletic",
    "usage": "Sports",
    "washCare": "Hand wash recommended",
    "lining": "Synthetic",
    "numberOfPockets": "",
    "sleeveStyling": "",
    "topHemline": "",
    "bottomHemline": "",
    "addOns": "Cushioning technology",
    "stitch": "Machine stitched",
    "character": "Professional",
    "productDetails": "Professional running shoe with advanced cushioning",
    "listViewName": "Nike Running Shoe",
    "materialCareDescription": "Mesh material with rubber sole",
    "sizeAndFitDescription": "True to size, wide fit available",
    "productDisplayName": "Nike Running Shoe - Black",
    "packageContains": "1 pair of shoes",
    "numberOfItems": "1",
    "tags": "running, sports, athletic, comfortable, mesh",
    "collectionName": "Performance",
    "ageGroup": "Adult",
    "season": "All season",
    "detectedBrand": "Nike",
    "sustainable": "Regular",
    "bottomClosure": "",
    "topClosure": "Lace",
    "styleNote": "Modern athletic design"
  },
  "product_name": "Nike Running Shoes",
  "images_analyzed": 3,
  "input_tokens": 2500,
  "output_tokens": 1200,
  "cost_inr": 1.85,
  "credits_deducted": 1,
  "timestamp": "2026-05-29T13:38:45.123456"
}
```

**Error Responses:**

401 Unauthorized:
```json
{
  "detail": "Unauthorized - Missing JWT token"
}
```

402 Insufficient Credits:
```json
{
  "detail": "Insufficient credits. You need 1 credit but have 0"
}
```

400 Bad Request:
```json
{
  "detail": "Maximum 5 images allowed per analysis"
}
```

---

## ❌ Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response normally |
| 400 | Bad Request | Check request format/data |
| 401 | Unauthorized | Refresh/re-login for new token |
| 402 | Insufficient Credits | Show "Add Credits" prompt |
| 404 | Not Found | Check endpoint URL |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Retry or contact support |

---

## 📚 Integration Guide

### Step 1: Setup Environment
```javascript
const API_BASE = 'http://127.0.0.1:8000';

// Helper function for authenticated requests
async function authenticatedFetch(endpoint, options = {}) {
  const token = localStorage.getItem('jwt_token');
  
  if (!token) {
    throw new Error('Not authenticated. Please login first.');
  }
  
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  if (response.status === 401) {
    localStorage.removeItem('jwt_token');
    window.location.href = '/login';
    throw new Error('Session expired. Please login again.');
  }
  
  return response;
}
```

### Step 2: Auth Flow
```javascript
// 1. Sign up
await fetch(`${API_BASE}/auth/signup`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(userData)
});

// 2. Login and save token
const loginRes = await fetch(`${API_BASE}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
const { access_token } = await loginRes.json();
localStorage.setItem('jwt_token', access_token);

// 3. Use authenticated endpoints
const credits = await authenticatedFetch('/api/credits');
```

### Step 3: Check Credits Before Analysis
```javascript
async function analyzeWithCreditCheck(productName, images) {
  // Check balance first
  const credits = await authenticatedFetch('/api/credits');
  
  if (credits.credits_remaining < 1) {
    alert('Insufficient credits! Add more credits to continue.');
    return null;
  }
  
  // Proceed with analysis
  return analyzeProduct(productName, images);
}
```

### Step 4: Display Results
```javascript
const result = await analyzeProduct(productName, images);

if (result) {
  console.log('Product Attributes:', result.analysis);
  console.log('Cost: ₹' + result.cost_inr);
  console.log('Tokens Used: ' + result.input_tokens + ' input, ' + result.output_tokens + ' output');
  
  // Update UI with analysis data
  displayAnalysisResults(result.analysis);
}
```

---

## 🎯 Frontend Checklist

- [ ] Implement signup form with all seller fields
- [ ] Implement login with token storage
- [ ] Add logout functionality (clear localStorage)
- [ ] Display credits balance on dashboard
- [ ] Implement product analysis with image upload
- [ ] Show analysis results
- [ ] Display usage history
- [ ] Add "Add Credits" functionality
- [ ] Implement error handling for all endpoints
- [ ] Add loading states during API calls
- [ ] Handle token expiration (401 errors)

---

## 🚀 Ready to Integrate!

All endpoints are documented and ready for frontend integration. Use the curl examples to test manually, then implement using the JavaScript/Fetch examples for your UI.

**Questions?** Check the error responses for specific issues, or review the cURL examples for correct request formats.
