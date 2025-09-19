# Simple Clerk Authentication

A streamlined authentication system for the AI Blog Generator using Clerk's hosted authentication pages.

## 🎯 Overview

This simple system redirects users to Clerk's hosted authentication page and handles the return flow seamlessly.

## ⚙️ Setup

### Environment Variables

Ensure these variables are set in your `.env` file:

```bash
FRONTEND_URL="https://your-clerk-hosted-page.clerk.accounts.dev"
CLERK_SECRET_KEY="sk_test_your_secret_key"
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_your_publishable_key"
```

### Configuration

1. **FRONTEND_URL**: Your Clerk hosted authentication page URL
2. **CLERK_SECRET_KEY**: Your Clerk secret key for token validation
3. **NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY**: Your Clerk publishable key

## 🚀 Usage

### Starting the Application

Simply run the Streamlit command:

```bash
streamlit run frontend/app.py
```

### Authentication Flow

1. **Unauthenticated State**: Users see a login button and disabled features
2. **Login Process**: Clicking login redirects to Clerk's hosted page
3. **Authentication**: Users authenticate using Clerk's interface
4. **Return Flow**: Users are redirected back with authentication token
5. **Authenticated State**: Features are enabled, user info displayed

## 🔒 Feature Protection

All AI features (Blog Generation, Image Generation, LinkedIn Posts, AI News) are protected and require authentication. The Home page is accessible without authentication.

## 🔧 Technical Details

### Authentication States

- **Unauthenticated**: Features disabled, login button shown
- **Authenticated**: All features enabled, user profile shown

### Session Management

Authentication state is maintained in Streamlit's session state:
- `st.session_state.authenticated`: Boolean authentication status
- `st.session_state.user_data`: User information from Clerk
- `st.session_state.user_email`: User's email address
- `st.session_state.username`: User's display name

### Token Handling

The system can handle multiple token formats from Clerk:
- JWT tokens in URL parameters
- Session tokens
- Direct user data parameters

## 🛠️ Development

### Adding New Protected Features

To protect a new feature, add authentication check:

```python
if self.auth_available and not is_authenticated():
    require_auth("Your Feature Name")
```

### Customizing Authentication

Modify `frontend/authentication/auth.py` to customize:
- Login URLs
- Token validation
- User data handling
- Authentication flow

## 🔍 Debugging

The system includes comprehensive logging. Check console output for:
- Authentication status
- Token validation results
- Redirect URL generation
- Session state management

## 📱 Features

### User Interface
- Clean login button in sidebar
- User profile display when authenticated
- Feature-specific authentication prompts
- Logout functionality

### Security
- JWT token validation
- Secure session management
- Protected feature access
- Clean logout process

## ⚡ Benefits

1. **Simple Setup**: Just run `streamlit run frontend/app.py`
2. **No Complex Dependencies**: Uses Clerk's hosted pages
3. **Secure**: Proper token validation and session management
4. **User-Friendly**: Clean, intuitive authentication flow
5. **Maintainable**: Minimal code, easy to understand and modify

## 🚨 Troubleshooting

### Common Issues

1. **Environment Variables**: Ensure all Clerk credentials are properly set
2. **FRONTEND_URL**: Verify the Clerk hosted page URL is correct
3. **Token Validation**: Check Clerk secret key is valid
4. **Redirects**: Ensure Clerk is configured with correct return URLs

### Logs

Check the terminal output for authentication-related messages:
- `✅ Simple Clerk authentication imported successfully`
- `🔧 Clerk Auth initialized with frontend URL: ...`
- `Token validated successfully for: ...`

This simple system provides robust authentication with minimal complexity, perfect for the AI Blog Generator's needs.
