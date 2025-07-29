# Enhanced Persona Feature Guide

## Overview

The Savvy Persona feature creates deeply personalized financial advisor experiences by analyzing user spending patterns and mapping them to cultural interests through the Qloo API. This creates a rich, contextually-aware persona that enables highly personalized financial advice.

## How It Works

### 1. Financial Data Analysis
- Extracts meaningful entities (brands, restaurants, services) from user bank transactions
- Identifies spending patterns and frequency
- Prioritizes entities that appear regularly (indicating lifestyle preferences)

### 2. Cultural Enrichment via Qloo API
- Sends extracted entities to Qloo's cultural intelligence API
- Maps financial entities to broader cultural interests (music, film, fashion, dining)
- Discovers correlated tastes and lifestyle patterns
- Generates personality indicators based on spending behavior

### 3. AI-Powered Persona Generation
- Uses Google Gemini to synthesize financial and cultural data
- Creates a comprehensive persona with:
  - **Persona Name**: Evocative identifier (e.g., "The Urban Wellness Seeker")
  - **Description**: Rich narrative combining lifestyle and financial identity
  - **Key Traits**: 3-5 personality characteristics
  - **Lifestyle Summary**: Daily habits, values, and experiences they prioritize
  - **Financial Tendencies**: Money mindset and spending philosophy
  - **Cultural Profile**: Music, entertainment, fashion, and dining preferences
  - **Advice Style**: How they prefer to receive financial guidance

### 4. Personalized Chat Experience
- When persona mode is enabled, the AI advisor uses the full persona context
- Responses reference user's specific traits, interests, and cultural preferences
- Advice aligns with their lifestyle values and spending patterns
- Language and examples resonate with their cultural context

## API Endpoints

### Check Persona Status
```
GET /api/v1/conversations/persona-status
```
Returns detailed persona information if it exists.

### Generate Persona
```
POST /api/v1/conversations/generate-persona
```
Creates or regenerates the user's persona profile.

### Generate Persona for Conversation
```
POST /api/v1/conversations/{conversation_id}/generate-persona
```
Creates persona in context of a specific conversation.

### Chat with Persona
```
POST /api/v1/conversations/chat
```
Include `"use_persona": true` in the request to enable persona-aware responses.

## Implementation Details

### Entity Extraction Algorithm
The system intelligently extracts entities from transaction descriptions by:
- Identifying capitalized words (potential brand names)
- Looking for business type indicators (RESTAURANT, CAFE, STORE, etc.)
- Prioritizing entities that appear multiple times
- Filtering out banking terminology
- Focusing on lifestyle-relevant spending categories

### Qloo Integration
- Uses Qloo's search API to find entity matches
- Calls insights API with entity IDs to discover cultural correlations
- Handles API failures gracefully with enhanced mock data
- Stores raw Qloo data for future analysis and improvements

### Persona Generation Prompt
The Gemini LLM receives a sophisticated prompt that:
- Explains the connection between spending and cultural identity
- Requests structured JSON output with specific fields
- Emphasizes the importance of cultural context in financial advice
- Instructs the AI to create actionable, personalized insights

### Database Schema
```sql
-- Enhanced persona_profiles table
CREATE TABLE persona_profiles (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE REFERENCES users(id),
    persona_name VARCHAR NOT NULL,
    persona_description VARCHAR NOT NULL,
    key_traits JSON, -- Array of trait strings
    lifestyle_summary VARCHAR,
    financial_tendencies VARCHAR,
    cultural_profile JSON, -- Music, film, fashion, dining preferences
    financial_advice_style VARCHAR,
    source_qloo_data JSON, -- Raw Qloo response for debugging
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## Frontend Integration

### Enable Persona in Chat
```typescript
const response = await chatWithAI({
    messages: [{ role: "user", content: "How should I budget for dining out?" }],
    use_persona: true,
    stream: true
}, accessToken, (chunk) => {
    // Handle streaming response
});
```

### Display Persona Information
```typescript
const personaStatus = await fetch('/api/v1/conversations/persona-status', {
    headers: { Authorization: `Bearer ${token}` }
});

if (personaStatus.has_persona) {
    // Show persona details
    console.log(`Persona: ${personaStatus.persona_name}`);
    console.log(`Cultural Profile:`, personaStatus.cultural_profile);
}
```

## Example Persona Output

```json
{
    "persona_name": "The Conscious Urban Explorer",
    "persona_description": "You are someone who values authentic experiences and mindful consumption. Your spending reflects a desire to explore your city's cultural offerings while maintaining awareness of quality and sustainability...",
    "key_traits": ["Curious", "Quality-Conscious", "Socially-Aware", "Experience-Oriented"],
    "lifestyle_summary": "Your daily routine likely includes visits to local coffee shops, trying new restaurants with friends, and investing in experiences over material possessions...",
    "financial_tendencies": "You tend to spend on experiences, quality food, and items that align with your values. You're willing to pay more for brands and services that reflect your identity...",
    "cultural_profile": {
        "music_taste": "Indie pop and alternative rock with appreciation for local artists",
        "entertainment_style": "Independent films, documentaries, and culturally diverse content",
        "fashion_sensibility": "Sustainable fashion with a focus on quality over quantity",
        "dining_philosophy": "Values local, organic, and ethically-sourced food experiences"
    },
    "financial_advice_style": "Prefers practical advice that acknowledges lifestyle values and includes sustainable spending strategies"
}
```

## Benefits

1. **Deeper Personalization**: Financial advice that truly understands the user's identity
2. **Cultural Relevance**: Recommendations that align with user's tastes and values
3. **Context-Aware Responses**: AI that references specific interests and lifestyle choices
4. **Engagement**: More relatable and engaging financial conversations
5. **Scalable**: Automatically generates personas without manual input

## Configuration

### Environment Variables
```bash
GEMINI_API_KEY=your_gemini_api_key
QLOO_API_KEY=your_qloo_api_key
```

### Qloo API Setup
The system uses Qloo's hackathon API endpoints:
- Search: `https://hackathon.api.qloo.com/search`
- Insights: `https://hackathon.api.qloo.com/v2/insights`

## Error Handling

The persona system gracefully handles:
- Missing transaction data (provides helpful error messages)
- Qloo API failures (uses enhanced mock data)
- Gemini API errors (logs errors and falls back to basic responses)
- Database connection issues (maintains conversation functionality)

## Future Enhancements

1. **Recommendation Engine**: Use Qloo data to suggest lifestyle-aligned financial products
2. **Persona Evolution**: Update personas as spending patterns change
3. **Multiple Personas**: Support different personas for different financial contexts
4. **Social Features**: Anonymous persona comparisons and insights
5. **Integration**: Connect with investment platforms and financial services that match persona traits

This enhanced persona feature transforms Savvy from a generic financial advisor into a truly personalized financial companion that understands not just what users spend, but who they are as people.
