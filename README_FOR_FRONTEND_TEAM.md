# 📚 Frontend Team - API Documentation Bundle

This folder contains everything your frontend team needs to build the UI for the Product Analyzer.

---

## 📄 Documentation Files

### 1. **API_DOCUMENTATION.md** ⭐ START HERE
**The complete API reference guide**
- All 6 endpoints with detailed explanations
- Request/response examples for each endpoint
- JavaScript/Fetch code snippets
- React component examples
- Integration guide for frontend
- Error handling instructions

👉 **Use this as your main reference document**

---

### 2. **API_QUICK_REFERENCE.md** 📋 CHEATSHEET
**Quick lookup guide**
- Summary table of all endpoints
- Quick curl commands
- JavaScript code snippets
- Response formats
- Error codes
- Frontend checklist

👉 **Use this when you need quick answers**

---

### 3. **CURL_COMMANDS.sh** 🔧 TESTING
**All curl commands in one file**
- Copy-paste ready curl commands
- One for each endpoint
- Easy for manual testing
- Replace placeholders (token, IDs, etc.)

👉 **Use this to manually test endpoints**

---

### 4. **Postman_Collection.json** 📮 POSTMAN
**Ready-to-import Postman collection**
- All endpoints configured
- Pre-filled request bodies
- Variable for JWT token
- No setup needed - just import

**How to import:**
1. Open Postman
2. Click "Import" → "Upload Files"
3. Select this file
4. Start testing

👉 **Use this for interactive API testing**

---

### 5. **FRONTEND_SETUP.md** 🎨 IMPLEMENTATION
**Step-by-step frontend guide**
- How to build signup form
- How to build login form
- Dashboard implementation
- Product analysis page
- Complete helper class (copy-paste ready)
- Frontend checklist

👉 **Use this to implement the UI**

---

## 🚀 Getting Started (3 Steps)

### Step 1: Read Documentation
```
Read: API_DOCUMENTATION.md (sections 1-3)
Time: 10 minutes
Learn: How each endpoint works
```

### Step 2: Test Endpoints
```
Use: Postman or CURL_COMMANDS.sh
Time: 15 minutes
Learn: What requests/responses look like
```

### Step 3: Build Frontend
```
Follow: FRONTEND_SETUP.md
Use: JavaScript code snippets
Time: 2-4 hours
Build: Complete UI
```

---

## 📋 All Endpoints Summary

```
POST /auth/signup          → Seller registration
POST /auth/login           → Get JWT token

GET  /api/credits          → Check balance
POST /api/credits/add      → Add credits
GET  /api/credits/history  → View usage

POST /api/analyse          → Analyze product images
```

**Base URL:** `http://127.0.0.1:8000`

---

## 🔑 Quick Copy-Paste Examples

### Login & Get Token
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

### Analyze Images
```bash
curl -X POST http://127.0.0.1:8000/api/analyse \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "product_name=Nike Shoes" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg"
```

---

## 🛠️ Copy-Paste Helper Class

From **FRONTEND_SETUP.md** → there's a complete `ProductAnalyzerAPI` class that you can copy directly into your project:

```javascript
class ProductAnalyzerAPI {
  async signup(data) { /* ... */ }
  async login(email, password) { /* ... */ }
  async logout() { /* ... */ }
  async getCredits() { /* ... */ }
  async addCredits(userId, amount) { /* ... */ }
  async getHistory() { /* ... */ }
  async analyzeProduct(productName, imageFiles) { /* ... */ }
}

// Usage
const api = new ProductAnalyzerAPI();
await api.login('email@example.com', 'password');
const credits = await api.getCredits();
const result = await api.analyzeProduct('Nike Shoes', [file1, file2]);
```

---

## 📱 Pages to Build

### Page 1: Signup
- Fields: email, password, first_name, last_name, seller_name, country, address, pincode, state, gst
- Action: POST /auth/signup
- Result: Show success message or error

### Page 2: Login
- Fields: email, password
- Action: POST /auth/login
- Result: Save JWT token to localStorage, redirect to dashboard

### Page 3: Dashboard
- Shows: Credit balance, add credits button
- Actions: GET /api/credits, POST /api/credits/add
- Components: Credits display, add credits form, usage history table

### Page 4: Product Analysis
- Fields: product name, image upload (5 max)
- Action: POST /api/analyse
- Result: Display 40+ product attributes in a table/form
- Optional: Download JSON, copy to clipboard, save to database

---

## ✅ Frontend Checklist

Essential features:
- [ ] Signup form with validation
- [ ] Login with token storage
- [ ] Dashboard with credits display
- [ ] Add credits functionality
- [ ] Product analysis with image upload
- [ ] Display analysis results (table/form)
- [ ] Usage history view
- [ ] Logout button
- [ ] Error messages (user-friendly)
- [ ] Loading states during API calls
- [ ] Token persistence (localStorage)
- [ ] Handle 401 errors (redirect to login)

Nice-to-have features:
- [ ] Download analysis as JSON
- [ ] Copy analysis to clipboard
- [ ] Export to CSV
- [ ] Dark mode
- [ ] Mobile responsive
- [ ] Input validation with feedback
- [ ] API error logging

---

## 🐛 Common Issues & Solutions

### "401 Unauthorized" Error
**Solution:** Token expired or not stored. Call login endpoint again and save the token.

### "402 Insufficient Credits" Error
**Solution:** User needs to add credits. Show "Add Credits" button/modal.

### CORS Error (if using external domain)
**Solution:** Server has CORS enabled. Should work from any origin.

### Images not uploading
**Solution:** Use FormData instead of JSON. Check file size limits.

### "Invalid JWT Token"
**Solution:** Token may be malformed or expired. Re-login to get new token.

---

## 🔐 Authentication Flow

```
1. User visits app
2. Check if jwt_token in localStorage
   ✓ Yes → Show dashboard
   ✗ No → Show login page
3. User enters email/password
4. POST /auth/login
5. Save access_token to localStorage
6. Redirect to dashboard
7. Use token in all future requests
8. If 401 error → Clear token, redirect to login
```

---

## 💾 State Management (Example)

```javascript
// Use localStorage or Context API or Redux

// Login
localStorage.setItem('jwt_token', response.access_token);
localStorage.setItem('user_id', response.user_id);

// Logout
localStorage.removeItem('jwt_token');
localStorage.removeItem('user_id');

// In requests
const token = localStorage.getItem('jwt_token');
headers['Authorization'] = `Bearer ${token}`;
```

---

## 📖 Reading Order for Frontend Team

1. **First 5 min:** Read this file (README_FOR_FRONTEND_TEAM.md)
2. **Next 10 min:** Skim API_QUICK_REFERENCE.md
3. **Next 20 min:** Read API_DOCUMENTATION.md (sections 1-3)
4. **Next 15 min:** Test endpoints using Postman
5. **Next 1 hour:** Build auth pages following FRONTEND_SETUP.md
6. **Final 1-2 hours:** Build dashboard and analysis pages

**Total: ~3-4 hours to complete**

---

## 🚀 Deployment Notes

**Development:**
- Base URL: `http://127.0.0.1:8000`
- Server running locally
- Test with curl/Postman first

**Production:**
- Update base URL in config
- Add HTTPS
- Update CORS settings
- Set secure cookies for token storage

---

## 📞 Questions?

Refer to:
- **API_DOCUMENTATION.md** → Full details with examples
- **API_QUICK_REFERENCE.md** → Quick answers
- **CURL_COMMANDS.sh** → See how endpoints work
- **FRONTEND_SETUP.md** → Implementation help

---

## 📦 File Summary

```
/product-analyser/
├── API_DOCUMENTATION.md          ← Full reference (start here)
├── API_QUICK_REFERENCE.md        ← Cheatsheet
├── CURL_COMMANDS.sh              ← Test commands
├── Postman_Collection.json       ← Import to Postman
├── FRONTEND_SETUP.md             ← Implementation guide
├── README_FOR_FRONTEND_TEAM.md   ← This file
├── .env                          ← Backend config
└── app/                          ← Backend code
```

---

## ✨ You Have Everything!

All documentation is complete and ready to use. Your frontend team can:
- ✅ Understand all endpoints
- ✅ Test with Postman
- ✅ Copy-paste code snippets
- ✅ Follow step-by-step guides
- ✅ Build the complete UI

**Good luck with development! 🚀**
