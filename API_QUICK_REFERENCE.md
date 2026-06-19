# 🚀 API Quick Reference

**Base URL:** `http://127.0.0.1:8000`

---

## 📌 All Endpoints Summary

| Method | Endpoint | Auth Required | Purpose |
|--------|----------|---------------|---------|
| POST | `/auth/signup` | ❌ No | Register new seller |
| POST | `/auth/login` | ❌ No | Get JWT token |
| GET | `/api/credits` | ✅ Yes | Check credit balance |
| POST | `/api/credits/add` | ✅ Yes | Add credits to user |
| GET | `/api/credits/history` | ✅ Yes | View usage history |
| POST | `/api/analyse` | ✅ Yes | Analyze product images |

---

## 🔑 Quick Curl Commands

### Sign Up
```bash
curl -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@company.com","password":"Pass123","first_name":"John","last_name":"Doe","seller_name":"JD Fashion","country":"India","address":"123 St","pincode":"110001","state":"Delhi","gst":"18AABCG1234H1Z0"}'
```

### Login (Get Token)
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@company.com","password":"Pass123"}'
```

### Check Credits
```bash
curl -X GET http://127.0.0.1:8000/api/credits \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Add Credits
```bash
curl -X POST http://127.0.0.1:8000/api/credits/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"USER_ID","amount":10}'
```

### Get History
```bash
curl -X GET http://127.0.0.1:8000/api/credits/history \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Analyze Images
```bash
curl -X POST http://127.0.0.1:8000/api/analyse \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "product_name=Nike Shoes" \
  -F "images=@img1.jpg" \
  -F "images=@img2.jpg"
```

---

## 🛠️ JavaScript Snippets

### Store Token After Login
```javascript
const loginRes = await fetch('http://127.0.0.1:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
const data = await loginRes.json();
localStorage.setItem('jwt_token', data.access_token);
```

### Get Credits
```javascript
const res = await fetch('http://127.0.0.1:8000/api/credits', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('jwt_token')}` }
});
const credits = await res.json();
console.log(credits.credits_remaining);
```

### Analyze Product
```javascript
const formData = new FormData();
formData.append('product_name', 'Nike Shoes');
formData.append('images', imageFile1);
formData.append('images', imageFile2);

const res = await fetch('http://127.0.0.1:8000/api/analyse', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${localStorage.getItem('jwt_token')}` },
  body: formData
});
const result = await res.json();
console.log(result.analysis);
```

---

## 📊 Response Summary

### Login Response
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user_id": "uuid",
  "email": "seller@company.com"
}
```

### Credits Response
```json
{
  "user_id": "uuid",
  "credits_remaining": 25,
  "credits_used": 5,
  "total_credits": 30
}
```

### Analysis Response
```json
{
  "analysis": { /* 40+ product attributes */ },
  "product_name": "Nike Shoes",
  "images_analyzed": 2,
  "input_tokens": 2500,
  "output_tokens": 1200,
  "cost_inr": 1.85,
  "credits_deducted": 1
}
```

---

## ⚠️ Error Codes

```
401 - Invalid or missing JWT token
400 - Bad request (invalid data/too many images)
402 - Insufficient credits
500 - Server error
```

---

## 🔐 Authentication Header Format

```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Always include this in requests to:**
- `/api/credits`
- `/api/credits/add`
- `/api/credits/history`
- `/api/analyse`

---

## 📋 Form Fields for Signup

```javascript
{
  email: "required (valid email)",
  password: "required",
  first_name: "required",
  last_name: "required",
  seller_name: "required",
  country: "required",
  address: "required",
  pincode: "required",
  state: "required",
  gst: "required (GST number)"
}
```

---

## 🎯 Analysis Request Format

**Method:** POST  
**Endpoint:** `/api/analyse`  
**Content-Type:** multipart/form-data

**Fields:**
- `product_name` (string, required)
- `images` (files, 1-5 images, required)

**Returns:** 40+ product attributes (color, fabric, occasion, pattern, etc.)

---

## 💰 Credits System

- **1 credit** = 1 product analysis (up to 5 images)
- Credits deducted **AFTER** successful analysis
- Check balance before analysis
- Show "Add Credits" if balance < 1

---

## 📱 Frontend Integration Checklist

- [ ] Signup form with all seller fields
- [ ] Login & token storage
- [ ] Dashboard showing credit balance
- [ ] Product analysis with image upload
- [ ] Display analysis results
- [ ] Add credits functionality
- [ ] Usage history view
- [ ] Logout (clear token)
- [ ] Error handling (401, 402, etc)
- [ ] Loading states

---

## 🚀 Deployment Notes

**Development:** `http://127.0.0.1:8000`  
**Production:** Update BASE_URL in frontend config

---

## 📞 Support

- Check API_DOCUMENTATION.md for full details
- Review curl examples for correct request format
- Verify JWT token is valid (may expire)
- Check server is running on port 8000
