# 🎨 Frontend Setup Guide - Product Analyzer

## 📦 What You're Building

A web/mobile application that allows sellers to upload product images and get AI-powered product details for e-commerce listings.

---

## 🚀 Quick Start for Frontend Team

### 1. API Base URL
```javascript
const API_BASE = 'http://127.0.0.1:8000';
```

### 2. Get the Documentation
You have 4 files to reference:

| File | Purpose |
|------|---------|
| **API_DOCUMENTATION.md** | Complete API reference with all endpoints |
| **API_QUICK_REFERENCE.md** | Cheatsheet with quick curl commands |
| **CURL_COMMANDS.sh** | All curl commands for testing |
| **Postman_Collection.json** | Import into Postman for easy testing |

---

## 📋 Complete Endpoint List

### Authentication (No Token Required)
```
POST /auth/signup      → Register seller
POST /auth/login       → Get JWT token
```

### Credits (Token Required)
```
GET  /api/credits      → Check balance
POST /api/credits/add  → Add credits
GET  /api/credits/history → View usage
```

### Analysis (Token Required)
```
POST /api/analyse      → Analyze product images
```

---

## 🔐 Authentication Flow

### Step 1: Signup Form
Create a form with these fields:

```html
<form>
  <input name="email" type="email" required />
  <input name="password" type="password" required />
  <input name="first_name" type="text" required />
  <input name="last_name" type="text" required />
  <input name="seller_name" type="text" required />
  <input name="country" type="text" required />
  <input name="address" type="text" required />
  <input name="pincode" type="text" required />
  <input name="state" type="text" required />
  <input name="gst" type="text" required />
</form>
```

### Step 2: Send Signup Request
```javascript
async function signup(formData) {
  const response = await fetch('http://127.0.0.1:8000/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
  
  const data = await response.json();
  if (response.ok) {
    alert('Signup successful! Please login.');
  } else {
    alert('Error: ' + data.detail);
  }
}
```

### Step 3: Login Form
```html
<form>
  <input name="email" type="email" required />
  <input name="password" type="password" required />
  <button>Login</button>
</form>
```

### Step 4: Send Login Request & Store Token
```javascript
async function login(email, password) {
  const response = await fetch('http://127.0.0.1:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  if (response.ok) {
    // Save token
    localStorage.setItem('jwt_token', data.access_token);
    localStorage.setItem('user_id', data.user_id);
    
    // Redirect to dashboard
    window.location.href = '/dashboard';
  } else {
    alert('Login failed: ' + data.detail);
  }
}
```

---

## 💳 Dashboard Features

### Show Credit Balance
```javascript
async function loadCredits() {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch('http://127.0.0.1:8000/api/credits', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  document.getElementById('credits').textContent = data.credits_remaining;
  document.getElementById('used').textContent = data.credits_used;
}
```

### Add Credits Button
```javascript
async function addCredits(amount) {
  const token = localStorage.getItem('jwt_token');
  const userId = localStorage.getItem('user_id');
  
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
  
  const data = await response.json();
  alert('Credits added! New balance: ' + data.new_balance);
  loadCredits(); // Refresh balance
}
```

### View Usage History
```javascript
async function loadHistory() {
  const token = localStorage.getItem('jwt_token');
  const response = await fetch('http://127.0.0.1:8000/api/credits/history', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const history = await response.json();
  
  const html = history.map(entry => `
    <tr>
      <td>${new Date(entry.created_at).toLocaleDateString()}</td>
      <td>${entry.input_tokens}</td>
      <td>${entry.output_tokens}</td>
      <td>₹${entry.cost_inr}</td>
    </tr>
  `).join('');
  
  document.getElementById('history').innerHTML = html;
}
```

---

## 📸 Product Analysis Page

### Image Upload Form
```html
<form id="analyzeForm">
  <input 
    id="productName" 
    type="text" 
    placeholder="Product Name (e.g., Nike Shoes)"
    required 
  />
  
  <input 
    id="imageUpload" 
    type="file" 
    multiple 
    accept="image/*"
    required 
  />
  
  <button type="submit">Analyze Product</button>
</form>

<div id="results"></div>
```

### Analyze Product Code
```javascript
const form = document.getElementById('analyzeForm');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const productName = document.getElementById('productName').value;
  const files = document.getElementById('imageUpload').files;
  
  // Check credits first
  const token = localStorage.getItem('jwt_token');
  const creditsRes = await fetch('http://127.0.0.1:8000/api/credits', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const credits = await creditsRes.json();
  
  if (credits.credits_remaining < 1) {
    alert('Insufficient credits! Please add more credits.');
    return;
  }
  
  // Prepare form data
  const formData = new FormData();
  formData.append('product_name', productName);
  
  // Add up to 5 images
  for (let i = 0; i < Math.min(files.length, 5); i++) {
    formData.append('images', files[i]);
  }
  
  // Show loading state
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = '<p>Analyzing images...</p>';
  
  try {
    // Send analysis request
    const response = await fetch('http://127.0.0.1:8000/api/analyse', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      resultsDiv.innerHTML = `<p style="color:red">Error: ${result.detail}</p>`;
      return;
    }
    
    // Display results
    displayAnalysisResults(result);
    
  } catch (error) {
    resultsDiv.innerHTML = `<p style="color:red">Error: ${error.message}</p>`;
  }
});

function displayAnalysisResults(result) {
  const resultsDiv = document.getElementById('results');
  
  const analysis = result.analysis;
  
  let html = `
    <h2>Product Analysis Results</h2>
    
    <div class="stats">
      <p><strong>Product:</strong> ${result.product_name}</p>
      <p><strong>Images Analyzed:</strong> ${result.images_analyzed}</p>
      <p><strong>Cost:</strong> ₹${result.cost_inr}</p>
      <p><strong>Credits Used:</strong> ${result.credits_deducted}</p>
      <p><strong>Tokens:</strong> ${result.input_tokens} input, ${result.output_tokens} output</p>
    </div>
    
    <div class="attributes">
      <h3>Product Attributes</h3>
      <table>
        <tr><th>Attribute</th><th>Value</th></tr>
  `;
  
  // Display all attributes
  for (const [key, value] of Object.entries(analysis)) {
    if (value) {
      html += `
        <tr>
          <td>${key.replace(/([A-Z])/g, ' $1').toUpperCase()}</td>
          <td>${value}</td>
        </tr>
      `;
    }
  }
  
  html += `
      </table>
      
      <div class="actions">
        <button onclick="copyToClipboard()">Copy JSON</button>
        <button onclick="downloadJSON()">Download JSON</button>
        <button onclick="saveToDB()">Save to Database</button>
      </div>
    </div>
  `;
  
  resultsDiv.innerHTML = html;
}

// Helper functions
function copyToClipboard() {
  const json = JSON.stringify(document.analyzeResult, null, 2);
  navigator.clipboard.writeText(json);
  alert('Copied to clipboard!');
}

function downloadJSON() {
  const json = JSON.stringify(document.analyzeResult, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'product-analysis.json';
  a.click();
}
```

---

## 🛠️ Complete Helper Function

```javascript
class ProductAnalyzerAPI {
  constructor(baseUrl = 'http://127.0.0.1:8000') {
    this.baseUrl = baseUrl;
  }

  // Auth
  async signup(data) {
    return this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async login(email, password) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    if (response.access_token) {
      localStorage.setItem('jwt_token', response.access_token);
      localStorage.setItem('user_id', response.user_id);
    }
    
    return response;
  }

  logout() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_id');
  }

  // Credits
  async getCredits() {
    return this.request('/api/credits', { requiresAuth: true });
  }

  async addCredits(userId, amount) {
    return this.request('/api/credits/add', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, amount }),
      requiresAuth: true
    });
  }

  async getHistory() {
    return this.request('/api/credits/history', { requiresAuth: true });
  }

  // Analysis
  async analyzeProduct(productName, imageFiles) {
    const formData = new FormData();
    formData.append('product_name', productName);
    
    for (let i = 0; i < Math.min(imageFiles.length, 5); i++) {
      formData.append('images', imageFiles[i]);
    }
    
    return this.request('/api/analyse', {
      method: 'POST',
      body: formData,
      requiresAuth: true,
      isFormData: true
    });
  }

  // Helper method
  async request(endpoint, options = {}) {
    const { requiresAuth, isFormData, ...fetchOptions } = options;

    const headers = isFormData ? {} : {
      'Content-Type': 'application/json',
      ...(fetchOptions.headers || {})
    };

    if (requiresAuth) {
      const token = localStorage.getItem('jwt_token');
      if (!token) throw new Error('Not authenticated');
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchOptions,
      headers
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'API Error');
    }

    return data;
  }
}

// Usage
const api = new ProductAnalyzerAPI();

// Signup
await api.signup({
  email: 'seller@company.com',
  password: 'Pass123',
  first_name: 'John',
  last_name: 'Doe',
  seller_name: 'JD Fashion',
  country: 'India',
  address: '123 St',
  pincode: '110001',
  state: 'Delhi',
  gst: '18AABCG1234H1Z0'
});

// Login
await api.login('seller@company.com', 'Pass123');

// Check credits
const credits = await api.getCredits();

// Analyze images
const result = await api.analyzeProduct('Nike Shoes', [file1, file2]);
```

---

## 🎯 Frontend Checklist

- [ ] Authentication pages (Signup, Login)
- [ ] Dashboard with credit balance
- [ ] Add credits functionality
- [ ] Usage history page
- [ ] Product analysis with image upload
- [ ] Display analysis results
- [ ] Error handling (show error messages)
- [ ] Loading states (show during API calls)
- [ ] Logout functionality
- [ ] Token persistence (localStorage)
- [ ] Token refresh on 401 error
- [ ] Form validation

---

## ⚠️ Important Notes

1. **Token Storage:** Use localStorage or sessionStorage
2. **Token Expiry:** Handle 401 errors by redirecting to login
3. **CORS:** If getting CORS errors, check server is running
4. **Max Images:** 5 images per analysis request
5. **Credits:** Check balance BEFORE allowing analysis
6. **Errors:** Always show user-friendly error messages

---

## 🧪 Testing with Postman

1. Import `Postman_Collection.json` into Postman
2. Update `{{jwt_token}}` variable after login
3. Test each endpoint
4. Use as reference for API implementation

---

## 📞 API Support

Refer to complete documentation:
- **API_DOCUMENTATION.md** - Full reference with examples
- **API_QUICK_REFERENCE.md** - Cheatsheet
- **CURL_COMMANDS.sh** - All curl examples

---

## 🚀 You're Ready!

You have all the information needed to build the frontend. Start with authentication, then build the dashboard and analysis features. Good luck! 🎉
