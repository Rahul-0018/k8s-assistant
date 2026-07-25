from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx
import json
import asyncio
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Groq AI Chatbot", version="1.0.0")

Instrumentator().instrument(app).expose(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    """
You are DevOpsGPT, an AI assistant specialized exclusively in DevOps, Cloud, Infrastructure, Platform Engineering, SRE, Kubernetes, and AI-powered Operations.

Your responsibilities include:
- Linux administration and shell scripting
- Docker, Docker Compose, and containerization
- Kubernetes, Helm, ArgoCD, GitOps, and Operators
- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins, Azure DevOps)
- Cloud platforms (AWS, Azure, GCP)
- Infrastructure as Code (Terraform, Ansible)
- Networking (HTTP/HTTPS, DNS, SSH, SSL/TLS, Load Balancers, Reverse Proxies, Firewalls)
- Monitoring and Observability (Prometheus, Grafana, Loki, ELK, OpenTelemetry)
- Service Mesh (Istio, Linkerd)
- Secret Management (Vault, Kubernetes Secrets)
- DevSecOps (Trivy, Snyk, SonarQube, OWASP, container security)
- Production architecture and best practices
- Troubleshooting infrastructure, Kubernetes, networking, and CI/CD failures
- AI-powered infrastructure automation and Kubernetes operations

Always:
- Provide accurate, production-ready, and secure solutions.
- Follow industry best practices.
- Explain commands before using them when appropriate.
- Prefer automation over manual processes.
- Recommend scalable and maintainable architectures.

If a user asks about topics unrelated to DevOps, Cloud, Infrastructure, Networking, SRE, Platform Engineering, Kubernetes, or AI for Operations, politely respond:

"I am a specialized DevOps Assistant and can only help with DevOps, Cloud, Kubernetes, Infrastructure, Networking, CI/CD, Observability, Security, and related engineering topics. Please ask a question within these domains."

Do not answer unrelated questions.
""",
)

# In-memory conversation store (use Redis in production)
conversations = {}


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = DEFAULT_MODEL
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    model: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "model": DEFAULT_MODEL,
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check - verifies Groq API connectivity"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured")
    return {"status": "ready", "api_configured": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat completion"""
    start_time = datetime.utcnow()

    # Get or create conversation
    conv_id = request.conversation_id or f"conv_{datetime.utcnow().timestamp()}"
    if conv_id not in conversations:
        conversations[conv_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add user message
    conversations[conv_id].append({"role": "user", "content": request.message})

    # Call Groq API
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": request.model,
        "messages": conversations[conv_id],
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            assistant_message = data["choices"][0]["message"]["content"]
            conversations[conv_id].append(
                {"role": "assistant", "content": assistant_message}
            )

            # Limit conversation history to last 20 messages
            if len(conversations[conv_id]) > 22:
                conversations[conv_id] = [conversations[conv_id][0]] + conversations[
                    conv_id
                ][-20:]

            latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ChatResponse(
                response=assistant_message,
                conversation_id=conv_id,
                model=request.model,
                tokens_used=data.get("usage", {}).get("total_tokens"),
                latency_ms=round(latency, 2),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Groq API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again in a moment.",
                )
            raise HTTPException(
                status_code=502, detail=f"Groq API error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat completion with SSE"""
    conv_id = request.conversation_id or f"conv_{datetime.utcnow().timestamp()}"
    if conv_id not in conversations:
        conversations[conv_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    conversations[conv_id].append({"role": "user", "content": request.message})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": request.model,
        "messages": conversations[conv_id],
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "stream": True,
    }

    async def event_generator():
        full_response = ""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST", GROQ_API_URL, json=payload, headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            # Store complete response
                            conversations[conv_id].append(
                                {"role": "assistant", "content": full_response}
                            )
                            yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get(
                                "delta", {}
                            ).get("content"):
                                content = chunk["choices"][0]["delta"]["content"]
                                full_response += content
                                yield f"data: {json.dumps({'content': content, 'conversation_id': conv_id})}\n\n"
                        except json.JSONDecodeError:
                            continue

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/models")
async def list_models():
    """List available Groq models with free tier limits"""
    return {
        "models": [
            {
                "id": "llama-3.1-8b-instant",
                "name": "Llama 3.1 8B",
                "rpm": 30,
                "rpd": 14400,
                "tpm": 6000,
            },
            {
                "id": "llama-3.3-70b-versatile",
                "name": "Llama 3.3 70B",
                "rpm": 30,
                "rpd": 1000,
                "tpm": 12000,
            },
            {
                "id": "meta-llama/llama-4-scout-17b-16e-instruct",
                "name": "Llama 4 Scout",
                "rpm": 30,
                "rpd": 1000,
                "tpm": 30000,
            },
            {
                "id": "openai/gpt-oss-20b",
                "name": "GPT-OSS 20B",
                "rpm": 30,
                "rpd": 1000,
                "tpm": 8000,
            },
            {
                "id": "qwen/qwen3-32b",
                "name": "Qwen3 32B",
                "rpm": 60,
                "rpd": 1000,
                "tpm": 6000,
            },
        ]
    }


@app.delete("/api/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation history"""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"status": "cleared", "conversation_id": conversation_id}


# HTML Chat UI
@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<link rel="stylesheet"
href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github-dark.min.css">

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chatbot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f23; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column;
        }
        .header { 
            background: #1a1a2e; padding: 18px 30px; border-bottom: 1px solid #2a2a4e;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header-right{
    display:flex;
    gap:15px;
    align-items:center;
}
        .header h1 { font-size: 20px; color: #00d4aa; }
        .model-select { 
            background: #2a2a4e; color: #e0e0e0; border: 1px solid #3a3a6e; 
            padding: 8px 16px; border-radius: 8px; cursor: pointer;
        }
        .chat-container{
    flex:1;
    overflow-y:auto;

    width:min(1400px,95vw);
    margin:0 auto;

    padding:30px 24px 180px;

    scrollbar-width:none;
}

.chat-container::-webkit-scrollbar{
    display:none;
}
}
        .message { margin: 25px 0; display:flex; width: 100p%}
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message-user { justify-content:flex-end }
        .message-user .bubble{

    width:fit-content;
    max-width:45%;

    background:linear-gradient(135deg,#00C9A7,#00A884);

    color:white;
}
        .message-assistant{ justify-content:flex-start;
}
        .message-assistant .bubble{
    background:#1D2035;
    border:1px solid #2f3554;
    color:#ECECEC;
}
        .bubble{
    padding:20px 24px;
    border-radius:18px;
    line-height:1.75;
    overflow-wrap:anywhere;
    word-break:break-word;
}
.input-area{
    position:sticky;
    bottom:0;
    width:100%;
    max-width:1100px;
    margin:auto;
    padding:40px;
    border-top:0px solid #2d2d4a;
    display:flex;
    gap:15px;
}

        .input-area input { 
            flex: 1; background: #252636; border: 1px solid #2a2a4e; 
            color: #e0e0e0; padding: 12px 18px; border-radius: 12px; font-size: 15px;
        }
        .input-area input:focus { outline: none; border-color: #00d4aa; }
        .input-area button { 
            background: #00d4aa; color: #0f0f23; border: none; 
            padding: 12px 24px; border-radius: 12px; cursor: pointer; font-weight: 600;
        }
        .input-area button:hover { background: #00b894; }
        .input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
        .typing{
    display:flex;
    gap:6px;
}

.typing-dot{
    width:8px;
    height:8px;
    border-radius:50%;
    background:#00D4AA;
    animation:typing 1.3s infinite;
}

.typing-dot:nth-child(2){
    animation-delay:.2s;
}

.typing-dot:nth-child(3){
    animation-delay:.4s;
}

@keyframes typing{

0%{
transform:translateY(0);
opacity:.4;
}

50%{
transform:translateY(-6px);
opacity:1;
}

100%{
transform:translateY(0);
opacity:.4;
}

}
        .latency { font-size: 11px; color: #666; margin-top: 4px; }
        .error { color: #ff6b6b; background: #2a1a1a; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
        .clear-btn { background: transparent; color: #666; border: 1px solid #2a2a4e; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .clear-btn:hover { color: #ff6b6b; border-color: #ff6b6b; }

        .disclaimer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    text-align: center;
    padding: 8px;
    font-size: 12px;
    color: #9ca3af;
    background: #0f0f23;
    border-top: 0px solid #2d2d4a;
    z-index: 100;
}
pre{
    background:#0B1220;
    border:1px solid #2E3445;
    border-radius:12px;
    overflow:auto;
    margin:18px 0;
    padding:0;
}

pre code{
    display:block;
    padding:18px;
    font-size:14px;
    line-height:1.7;
    font-family:JetBrains Mono,Consolas,monospace;
}

.code-toolbar{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:10px 15px;
    background:#151C2D;
    border-bottom:1px solid #2E3445;
}

.code-language{
    color:#94A3B8;
    font-size:12px;
    font-weight:600;
    letter-spacing:1px;
}

.copy-btn{
    background:#0e1524;
    color:#94A3B8;
    border:none;
    padding:6px 12px;
    border-radius:6px;
    cursor:pointer;
    font-size:12px;
    transition:.25s;
}

.copy-btn:hover{
    background:#0e1524;
}

:not(pre)>code{
    background:#1E293B;
    color:#38BDF8;
    padding:3px 6px;
    border-radius:5px;
}
.hljs{
    background:transparent !important;
    padding:18px !important;
}

pre{
    position:relative;
}

.code-toolbar{
    position:sticky;
    top:0;
    z-index:1;
}
/* Chat bubble */
.message{
    display:flex;
    width:100%;
    margin:20px 0;
}

.message-assistant{
    justify-content:flex-start;
}

.message-user{
    justify-content:flex-end;
}

/* Assistant */
.message-assistant .bubble{
    width:100%;
    max-width:900px;          /* or 90% */
    background:#1D2035;
    border:1px solid #2f3554;
    color:#ECECEC;
}

/* User */
.message-assistant .bubble{

    width:100%;
    max-width:1100px;

    background:#1D2035;
    border:1px solid #2f3554;

    color:#ECECEC;
}




/* Markdown container */
.bubble>*:first-child{
    margin-top:0;
}

.bubble>*:last-child{
    margin-bottom:0;
}

.bubble p{
    margin:0 0 14px;
}

.bubble h1,
.bubble h2,
.bubble h3,
.bubble h4{
    margin:18px 0 12px;
    font-weight:700;
    line-height:1.3;
}

.bubble ul,
.bubble ol{
    margin:12px 0;
    padding-left:28px;
}

.bubble li{
    margin:8px 0;
    line-height:1.7;
}

.bubble li>p{
    margin:0;
}

.bubble blockquote{
    margin:16px 0;
    padding-left:16px;
    border-left:4px solid #00D4AA;
}

.bubble hr{
    border:none;
    border-top:1px solid #3A405C;
    margin:20px 0;
}

.bubble table{
    width:100%;
    border-collapse:collapse;
    margin:16px 0;
}

.bubble th,
.bubble td{
    padding:10px 14px;
    border:1px solid #374151;
    text-align:left;
}

.bubble img{
    max-width:100%;
    border-radius:10px;
}
.input-area{
    position:sticky;
    bottom:50px;

    width:100%;
    max-width:900px;

    margin:0 auto;
    padding:16px;

    display:flex;
    align-items:flex-end;
    gap:12px;

    background:#1D2035;
    border:1px solid #2f3554;
    border-radius:22px;
}

#userInput{
    flex:1;

    min-height:24px;
    max-height:180px;

    resize:none;
    overflow-y:auto;

    scrollbar-width:none;
    -ms-overflow-style:none;

    background:#1D2035;
    border:none;
    outline:none;

    color:#ECECEC;

    font-size:15px;
    line-height:1.6;
    font-family:inherit;

    padding:6px 0;
}
#userInput::-webkit-scrollbar{
    display:none;
}

#userInput::placeholder{
    color:#8b93a7;
}

#sendBtn{
    width:42px;
    height:42px;

    border:none;
    border-radius:50%;

    background:#10A37F;
    color:#fff;

    display:flex;
    align-items:center;
    justify-content:center;

    cursor:pointer;

    transition:.2s;
}

#sendBtn:hover{
    background:#0d8b6d;
}

#sendBtn:disabled{
    opacity:.5;
}

pre{
    width:100%;
    max-width:100%;

    overflow-x:auto;

    margin:18px 0;

    border-radius:12px;
}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 AI Chatbot</h1>
        <div style="display:flex;gap:12px;align-items:center;">
            <button class="clear-btn" onclick="clearChat()">🗑️ Clear</button>
            <select class="model-select" id="modelSelect">
                <option value="llama-3.1-8b-instant">Llama 3.1 8B (Fast)</option>
            </select>
        </div>
    </div>
    <div class="chat-container" id="chatContainer">
        <div class="message message-assistant">
            <div class="bubble">Hello! I'm your DevOps AI Assistant. I can help you with Kubernetes, Docker, Linux, CI/CD, Cloud, Terraform, Ansible, Networking, Monitoring, and Infrastructure troubleshooting. How can I assist you today?</div>
        </div>
    </div>
    <div class="input-area">
    <textarea
    id="userInput"
    rows="1"
    placeholder="Type your message..."
></textarea>
        <button id="sendBtn" onclick="sendMessage()">➤</button>
    </div>
    <div class="disclaimer">
    AI can make mistakes. Check important information.
</div>
    <script>
        let conversationId = null;
        let isStreaming = true;

        let isGenerating = false;
const input = document.getElementById("userInput");

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
});

input.addEventListener("keydown", async (e) => {

    if (isGenerating) {
        e.preventDefault();
        return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        await sendMessage();
    }

});
        function addMessage(text,isUser,latency){

    const container=document.getElementById("chatContainer");

    const msgDiv=document.createElement("div");

    msgDiv.className=`message ${isUser?"message-user":"message-assistant"}`;

    msgDiv.innerHTML=
    `<div class="bubble">${renderMarkdown(text)}</div>
    ${latency?`<div class="latency">⚡ ${latency}ms</div>`:""}`;

    const bubble=msgDiv.querySelector(".bubble");

    bubble.querySelectorAll("pre code").forEach(block=>{
        hljs.highlightElement(block);
    });

    addCopyButtons(bubble);

    container.appendChild(msgDiv);

    container.scrollTo({
        top:container.scrollHeight,
        behavior:"smooth"
    });

}

        function showTyping() {
            const container = document.getElementById('chatContainer');
            const typingDiv = document.createElement('div');
            typingDiv.id = 'typing';
            typingDiv.className = 'message message-assistant';
            typingDiv.innerHTML = '<div class="bubble typing"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';
            container.appendChild(typingDiv);
            container.scrollTop = container.scrollHeight;
        }

        function removeTyping() {
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }

        marked.setOptions({
    gfm:true,
    breaks:true,

    highlight:function(code,lang){

        if(lang && hljs.getLanguage(lang)){
            return hljs.highlight(code,{language:lang}).value;
        }

        return hljs.highlightAuto(code).value;

    }
});

function renderMarkdown(text) {
    return marked.parse(text);
}

function addCopyButtons(container){

    container.querySelectorAll("pre").forEach(pre=>{

        if(pre.querySelector(".copy-btn")) return;

        const code=pre.querySelector("code");
        if(!code) return;

        const wrapper=document.createElement("div");
        wrapper.className="code-toolbar";

        const lang=document.createElement("span");
        lang.className="code-language";

        let language="TEXT";

        code.className.split(" ").forEach(cls=>{
            if(cls.startsWith("language-")){
                language=cls.replace("language-","").toUpperCase();
            }
        });

        lang.textContent=language;

        const btn=document.createElement("button");
        btn.className="copy-btn";
        btn.innerHTML="Copy";

        btn.onclick=async()=>{

            await navigator.clipboard.writeText(code.textContent);

            btn.innerHTML="Copied";

            setTimeout(()=>{
                btn.innerHTML="Copy";
            },2000);

        };

        wrapper.appendChild(lang);
        wrapper.appendChild(btn);

        pre.insertBefore(wrapper,code);

    });

}
        async function sendMessage() {
        if (isGenerating)
        return;

    isGenerating = true;

    const btn = document.getElementById("sendBtn");

    const text = input.value.trim();

    if (!text) return;

    input.value = "";
    input.style.height = "auto";

    btn.disabled = true;
    input.placeholder = "AI is generating...";

    addMessage(text, true);

    showTyping();

    const model = document.getElementById("modelSelect").value;

    try {

        if (isStreaming) {
            await sendStreaming(text, model);
        } else {
            await sendNonStreaming(text, model);
        }

    } finally {

        isGenerating = false;

btn.disabled = false;

input.disabled = false;

input.placeholder = "Type your message...";

input.focus();

    }

}

        async function sendStreaming(text, model) {
    const container = document.getElementById('chatContainer');

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-assistant';

    const bubbleId = 'stream-' + Date.now();

    msgDiv.innerHTML = `
        <div class="bubble">
            <span id="${bubbleId}"></span>
        </div>
    `;

    container.appendChild(msgDiv);

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: text,
                conversation_id: conversationId,
                model: model
            })
        });

        removeTyping();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = '';
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.done) {
                        conversationId = data.conversation_id;
                    } else if (data.content) {
                        fullText += data.content;
                        const bubble = document.getElementById(bubbleId);

bubble.innerHTML = renderMarkdown(fullText);

bubble.querySelectorAll("pre code").forEach(block=>{
    hljs.highlightElement(block);
});

addCopyButtons(bubble);

                        container.scrollTop =
                            container.scrollHeight;
                    }

                } catch (e) {
                    console.error(e);
                }
            }
        }

    } catch (err) {
        removeTyping();
        addMessage('Error: ' + err.message, false);
    }
}

        async function sendNonStreaming(text, model) {
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, conversation_id: conversationId, model: model })
                });

                removeTyping();

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Request failed');
                }

                const data = await response.json();
                conversationId = data.conversation_id;
                addMessage(data.response, false, data.latency_ms);
            } catch (err) {
                removeTyping();
                addMessage('Error: ' + err.message, false);
            }
        }

        async function clearChat() {
            if (conversationId) {
                await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' });
            }
            conversationId = null;
            document.getElementById('chatContainer').innerHTML = `
                <div class="message message-assistant">
                    <div class="bubble">Hello! I'm your DevOps AI Assistant. I can help you with Kubernetes, Docker, Linux, CI/CD, Cloud, Terraform, Ansible, Networking, Monitoring, and Infrastructure troubleshooting. How can I assist you today?</div>
                </div>
            `;
        }
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
