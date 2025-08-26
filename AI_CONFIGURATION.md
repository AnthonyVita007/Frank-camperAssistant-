# Frank Camper Assistant - AI Module Configuration

## Overview

The AI module enables Frank to respond to non-command text using Google Gemini API. The system automatically distinguishes between commands (starting with `/`) and conversational AI requests.

## Setup

### 1. Get Google Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the generated key

### 2. Configure Environment Variable

Set the API key as an environment variable:

```bash
export GOOGLE_GEMINI_API_KEY='your-api-key-here'
```

For permanent configuration, add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
echo 'export GOOGLE_GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Verify Configuration

Start the application and check the logs:

```bash
python app.py
```

You should see:
- `[AIHandler] AI handler initialized successfully` (if API key is valid)
- `[AIHandler] AI handler initialized but AI processor is not available` (if API key is missing/invalid)

## Usage

### Commands (existing functionality)

Commands starting with `/` are processed by the command system:

- `/clear` - Clear the console
- `/debugmode` - Switch to debug mode  
- `/usermode` - Switch to user mode

### AI Requests (new functionality)

Any text not starting with `/` is sent to the AI system:

- `"Ciao Frank!"` → Conversational response
- `"Che tempo fa?"` → AI-generated answer
- `"Consigli per viaggi in camper"` → Travel advice

## Architecture

```
User Input
    ↓
CommunicationHandler
    ↓
Is it a command? (starts with /)
    ↓                    ↓
   YES                  NO
    ↓                    ↓
CommandProcessor    AIHandler
    ↓                    ↓
Execute Command     AIProcessor
    ↓                    ↓
CommandResult       Google Gemini API
    ↓                    ↓
Frontend Response   AIResponse
                         ↓
                    Frontend Response
```

## API Configuration Details

### Model Configuration

Default model: `gemini-1.5-flash`

Configuration parameters:
- `temperature`: 0.7 (creativity level)
- `top_p`: 0.8 (nucleus sampling)
- `top_k`: 64 (token selection)
- `max_output_tokens`: 8192 (response length)

### Safety Settings

The AI system includes safety filters for:
- Harassment
- Hate speech
- Sexually explicit content
- Dangerous content

### Rate Limiting & Retry Logic

- Maximum retries: 3 attempts
- Timeout: 30 seconds per request
- Exponential backoff for failed requests

## Error Handling

The system gracefully handles:

1. **Missing API Key**: AI features disabled, commands still work
2. **API Errors**: User sees friendly error message, request is logged
3. **Network Issues**: Automatic retry with backoff
4. **Invalid Responses**: Fallback error messages

## Troubleshooting

### AI not responding

1. Check API key configuration:
   ```bash
   echo $GOOGLE_GEMINI_API_KEY
   ```

2. Check application logs for errors

3. Verify API key is valid at [Google AI Studio](https://makersuite.google.com/)

### Commands not working

Commands should work regardless of AI configuration. If `/clear`, `/debugmode`, or `/usermode` don't work, check the command processor logs.

### Mixed responses

Make sure commands start with `/` exactly. Input like `/ clear` (with space) will be treated as AI request, not a command.