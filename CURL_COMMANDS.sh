#!/bin/bash

# ============================================
# PRODUCT ANALYZER API - CURL COMMANDS
# ============================================
# Replace YOUR_JWT_TOKEN with actual token from login response

API_BASE="http://127.0.0.1:8000"

# ============================================
# 1. SIGN UP
# ============================================
echo "=== 1. SIGNUP ==="
curl -X POST $API_BASE/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@company.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "seller_name": "JD Fashion Pvt Ltd",
    "country": "India",
    "address": "123 Market Street",
    "pincode": "110001",
    "state": "Delhi",
    "gst": "18AABCG1234H1Z0"
  }'
echo -e "\n\n"

# ============================================
# 2. LOGIN
# ============================================
echo "=== 2. LOGIN (Get JWT Token) ==="
curl -X POST $API_BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@company.com",
    "password": "SecurePass123"
  }'
echo -e "\n\n"

# ============================================
# 3. GET CREDIT BALANCE
# ============================================
echo "=== 3. GET CREDIT BALANCE ==="
curl -X GET $API_BASE/api/credits \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
echo -e "\n\n"

# ============================================
# 4. ADD CREDITS
# ============================================
echo "=== 4. ADD CREDITS ==="
curl -X POST $API_BASE/api/credits/add \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 10
  }'
echo -e "\n\n"

# ============================================
# 5. GET USAGE HISTORY
# ============================================
echo "=== 5. GET USAGE HISTORY ==="
curl -X GET $API_BASE/api/credits/history \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
echo -e "\n\n"

# ============================================
# 6. ANALYZE PRODUCT (with image files)
# ============================================
echo "=== 6. ANALYZE PRODUCT IMAGES ==="
curl -X POST $API_BASE/api/analyse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "product_name=Nike Running Shoes" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "images=@image3.jpg"
echo -e "\n\n"

# ============================================
# NOTES:
# ============================================
# 1. Replace YOUR_JWT_TOKEN with token from login response
# 2. Replace 550e8400-e29b-41d4-a716-446655440000 with actual user_id
# 3. Replace image1.jpg, image2.jpg, image3.jpg with actual image paths
# 4. Maximum 5 images per analysis request
# 5. All image endpoints require valid JWT token
# ============================================
