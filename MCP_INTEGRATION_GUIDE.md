# MCP Integration & Enhanced AI Setup Guide

This guide will help you integrate the Fi MCP server with your Savvy backend to provide comprehensive financial data awareness to your AI advisor.

## Overview

The integration adds three key enhancements:

1. **MCP Client Integration**: Direct connection to Fi Money's financial data
2. **Enhanced AI Framework**: LangGraph-based conversation state management  
3. **Multi-Model Support**: OpenAI, Anthropic, Google Gemini integration

## Prerequisites

1. **Fi MCP Server**: Running locally or accessible via network
2. **API Keys**: Google Gemini, optionally OpenAI and Anthropic
3. **Python Environment**: Updated dependencies

## Installation Steps

### 1. Install Enhanced Dependencies

```bash
cd /Users/anas/development/projects/savvy-backend
pip install -r requirements.txt
```

New dependencies added:
- `langchain-anthropic==0.3.18`
- `langchain-google-genai==2.0.7` 
- `langgraph==0.2.80`
- `mcp==0.9.2`
- Updated `httpx==0.28.1`

### 2. Environment Configuration

Add these variables to your `.env` file:

```bash
# MCP Integration
MCP_SERVER_URL=http://localhost:8080
MCP_DEFAULT_PHONE=2222222222

# Enhanced AI Models
ANTHROPIC_API_KEY=your_anthropic_key_here
COHERE_API_KEY=your_cohere_key_here  
HUGGINGFACE_API_KEY=your_huggingface_key_here

# AI Configuration
DEFAULT_AI_MODEL=gemini
CONVERSATION_MEMORY_LIMIT=20
MAX_CONTEXT_LENGTH=8000

# Performance Settings
ENABLE_MCP_CACHE=true
MCP_CACHE_TTL=300
ENABLE_RESPONSE_STREAMING=true
```

### 3. Start Fi MCP Server

If you haven't already, start the Fi MCP server:

```bash
cd /Users/anas/development/projects/fi-mcp-dev
FI_MCP_PORT=8080 go run .
```

The server will be available at `http://localhost:8080`

### 4. Database Schema Updates

The integration works with your existing database schema. No migrations required.

### 5. Update API Routes

Add the MCP insights routes to your main API router.

In `app/main.py`, add:

```python
from app.api.routes import mcp_insights

app.include_router(
    mcp_insights.router,
    prefix="/api/v1/mcp",
    tags=["mcp-insights"]
)
```

## Usage Guide

### 1. Check MCP Integration Status

```bash
curl -X GET "http://localhost:5000/api/v1/mcp/mcp-status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Setup MCP for a User

```bash
curl -X POST "http://localhost:5000/api/v1/mcp/setup-mcp" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "2222222222"}'
```

### 3. Get MCP Financial Insights

```bash
curl -X GET "http://localhost:5000/api/v1/mcp/mcp-insights" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Enhanced AI Chat

The existing `/api/v1/conversations/chat` endpoint now automatically:

1. **Detects Financial Queries**: Analyzes user intent for financial topics
2. **Loads MCP Data**: Retrieves real-time financial information
3. **Enhances Context**: Builds comprehensive prompts with financial data
4. **Streams Responses**: Provides real-time AI responses with financial awareness

## Features Enabled

### MCP Financial Data Integration

- **Net Worth Analysis**: Real-time asset and liability tracking
- **Investment Portfolio**: Mutual funds, stocks, EPF details
- **Credit Monitoring**: Credit scores and loan information
- **Transaction Analysis**: Bank transaction patterns and insights
- **Goal Tracking**: Financial goal progress monitoring

### Enhanced AI Capabilities

- **Context Awareness**: Comprehensive financial context in all responses
- **Multi-Model Support**: GPT-4, Claude, Gemini model options
- **State Management**: LangGraph-based conversation state tracking
- **Streaming Responses**: Real-time response generation
- **Persona Integration**: Enhanced personas with MCP financial data

### Example Enhanced Responses

**Before MCP Integration:**
```
"I'd recommend diversifying your investments based on general principles."
```

**After MCP Integration:**
```
"Based on your current portfolio of ₹84,642 in mutual funds and ₹211,111 in EPF, 
I can see you're already building a solid foundation. Your net worth of ₹658,305 
shows good progress, but I notice you have a ₹5,000 vehicle loan. 

Given your investment style and current allocation, I'd recommend:
1. Increasing your equity mutual fund allocation by 10%
2. Consider adding international funds for better diversification
3. Your EPF contribution is strong - maintain this for long-term wealth building"
```

## Testing the Integration

### 1. Test MCP Connection

```python
from app.services.mcp_client import mcp_client

# Test authentication
success = await mcp_client.authenticate("2222222222")
print(f"MCP Authentication: {success}")

# Get financial profile
profile = await mcp_client.get_comprehensive_financial_profile("2222222222")
print(f"Net Worth: {profile.net_worth}")
```

### 2. Test Enhanced AI Service  

```python
from app.services.mcp_ai_integration import mcp_ai_service

# Test enhanced response
response = await mcp_ai_service.generate_enhanced_response(
    db, user_id, messages, use_persona=True
)
print(f"Enhanced Response: {response}")
```

### 3. Frontend Integration

Update your frontend to use the enhanced features:

```typescript
// Check MCP status
const mcpStatus = await fetch('/api/v1/mcp/mcp-status');

// Setup MCP integration
const setupMcp = await fetch('/api/v1/mcp/setup-mcp', {
  method: 'POST',
  body: JSON.stringify({ phone_number: userPhone })
});

// Get enhanced insights
const insights = await fetch('/api/v1/mcp/mcp-insights');
```

## Troubleshooting

### Common Issues

1. **MCP Server Connection Failed**
   - Ensure Fi MCP server is running on port 8080
   - Check firewall settings
   - Verify MCP_SERVER_URL in environment

2. **Authentication Failed**
   - Verify phone number is in Fi MCP test data
   - Check MCP server logs for authentication errors
   - Try different test phone numbers (2222222222, 3333333333, etc.)

3. **Enhanced AI Not Working**
   - Check API keys are properly configured
   - Verify all dependencies are installed
   - Review application logs for import errors

4. **Database Connection Issues**
   - Ensure PostgreSQL is running
   - Check database URL configuration
   - Verify user table has phone_number field

### Log Monitoring

Monitor these log patterns:

```bash
# MCP Integration
tail -f logs/app.log | grep "MCP"

# Enhanced AI
tail -f logs/app.log | grep "Enhanced AI"

# Database Connection
tail -f logs/app.log | grep "Database"
```

## Performance Optimization

### 1. Enable Caching

```bash
ENABLE_MCP_CACHE=true
MCP_CACHE_TTL=300  # 5 minutes
```

### 2. Connection Pooling

The MCP client uses connection pooling for optimal performance:

```python
# Automatic connection management
mcp_client = MCPClient()  # Reuses connections
```

### 3. Streaming Optimization

```bash
ENABLE_RESPONSE_STREAMING=true
CONVERSATION_MEMORY_LIMIT=20  # Limit context size
MAX_CONTEXT_LENGTH=8000       # Prevent token limits
```

## Security Considerations

1. **API Keys**: Store securely in environment variables
2. **Phone Numbers**: Validate and sanitize input
3. **MCP Data**: Cache responsibly with appropriate TTL
4. **User Privacy**: Follow data protection guidelines

## Next Steps

1. **Deploy to Production**: Update environment variables for production MCP server
2. **Add More Models**: Integrate additional AI providers
3. **Advanced Analytics**: Build financial trend analysis
4. **Mobile Integration**: Extend MCP features to mobile app
5. **Custom Insights**: Develop domain-specific financial insights

The integration provides a solid foundation for building sophisticated, context-aware financial AI advisory services.
