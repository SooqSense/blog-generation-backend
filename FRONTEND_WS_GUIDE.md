# Next.js Guide: Real-time Blog Generation (WebSocket)

This guide provides a comprehensive blueprint for implementing the frontend streaming logic in Next.js to work with our Django Channels backend. It covers authentication, state management, and real-time UI rendering.

---

## 1. Connection Architecture

The backend uses **Django Channels** and **Redis** to stream tokens (chunks) as they are generated. 

### WebSocket URL Structure
`ws://<backend-domain>/ws/stream/?token=<CLERK_JWT_TOKEN>`

> **Security Note**: We pass the Clerk token as a query parameter because standard browser WebSocket APIs do not support custom headers. Our `ClerkWebSocketAuthMiddleware` on the backend is specifically configured to handle this.

---

## 2. The Custom Hook: `useBlogGenerator`

We recommend encapsulating the WebSocket logic in a custom hook to keep your components clean.

```typescript
// hooks/useBlogGenerator.ts
import { useState, useEffect, useRef, useCallback } from 'react';

export type Section = {
  id: string;
  title: string;
  content: string;
  image_url?: string;
  status: 'pending' | 'writing' | 'completed' | 'error';
};

export const useBlogGenerator = () => {
  const [sections, setSections] = useState<Section[]>([]);
  const [status, setStatus] = useState<string>('Idle');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const startGeneration = useCallback((topic: string, clerkToken: string, options: any = {}) => {
    setIsGenerating(true);
    setSections([]);
    setError(null);

    // 1. Establish connection
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/stream/?token=${clerkToken}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      // 2. Start generation task
      socket.send(JSON.stringify({
        type: 'generate_blog',
        topic,
        ...options
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'status':
          setStatus(data.message);
          break;

        case 'toc_complete':
          // Initializing the structured state based on the TOC
          const initialSections = data.sections.map((s: any) => ({
            id: s.id,
            title: s.title,
            content: '',
            status: 'pending'
          }));
          setSections(initialSections);
          break;

        case 'section_token':
          // Append tokens to the specific section in real-time
          setSections(prev => prev.map(s => 
            s.id === data.section_id 
              ? { ...s, content: s.content + data.content, status: 'writing' } 
              : s
          ));
          break;

        case 'image':
          // Update section image
          setSections(prev => prev.map(s => 
            s.id === data.section_id ? { ...s, image_url: data.image_url } : s
          ));
          break;

        case 'section_complete':
          setSections(prev => prev.map(s => 
            s.id === data.section_id ? { ...s, status: 'completed' } : s
          ));
          break;

        case 'complete':
          setIsGenerating(false);
          setStatus('Completed');
          socket.close();
          break;

        case 'error':
          setError(data.message);
          setIsGenerating(false);
          break;
      }
    };

    socket.onerror = (err) => {
      setError("Connection error");
      setIsGenerating(false);
    };

    socket.onclose = () => setIsGenerating(false);
  }, []);

  return { sections, status, isGenerating, error, startGeneration };
};
```

---

## 3. UI Component Implementation

Use `react-markdown` to render the content as it streams. This creates a "Typewriter" effect as the blog grows.

```tsx
// components/BlogGenerationView.tsx
import ReactMarkdown from 'react-markdown';
import { useBlogGenerator } from '../hooks/useBlogGenerator';

export const BlogGenerationView = () => {
  const { sections, status, isGenerating, startGeneration } = useBlogGenerator();

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header & Controls */}
      <div className="mb-8 p-4 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-bold">Status: {status}</h2>
        {!isGenerating && (
          <button 
            onClick={() => startGeneration("Future of AI", "clerk_token_here")}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded"
          >
            Start Generation
          </button>
        )}
      </div>

      {/* The Dynamic Content Stream */}
      <div className="space-y-12">
        {sections.map((section) => (
          <section key={section.id} className="animate-fade-in">
            <h2 className="text-3xl font-bold mb-4">{section.title}</h2>
            
            {section.image_url && (
              <img 
                src={section.image_url} 
                alt={section.title} 
                className="w-full h-96 object-cover rounded-xl mb-6 shadow-lg"
              />
            )}

            <div className="prose prose-lg max-w-none">
              <ReactMarkdown>{section.content}</ReactMarkdown>
            </div>

            {section.status === 'writing' && (
              <span className="inline-block w-2 h-5 bg-blue-500 animate-pulse ml-1" />
            )}
          </section>
        ))}
      </div>
    </div>
  );
};
```

---

## 4. Crucial Implementation Details

### A. Auto-Scrolling
To keep the "active" section in view, use `useEffect` to scroll to the bottom whenever `sections` update:
```tsx
const scrollRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (isGenerating) {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }
}, [sections, isGenerating]);
```

### B. Handling Markdown Stability
Because tokens arrive as fragments (e.g., `*`, `*Important`, `**`), `react-markdown` might blink or render partial bold tags. 
- **Solution**: The `astream` on the backend is tuned to deliver tokens that are usually complete words, but on the frontend, using `prose` (Tailwind Typography) ensures the layout shifts are minimal.

### C. State Buffering vs. Direct State
For extremely high-speed streaming (10+ tokens per second), updating React state on every token can hurt performance.
- **Optimization**: You can buffer tokens in a `ref` and update the visible state every 100ms using a `setInterval` or `requestAnimationFrame` when the generation is active.

### D. Sequential vs. Parallel Rendering
The backend generates sections **in parallel** to save time. 
- Our `toc_complete` event gives you the "slots" first.
- As tokens arrive for different sections simultaneously, the UI will show multiple sections "growing" at the same time. This is a massive "WOW" factor for users compared to sequential line-by-line generators.

---

## 5. Summary of Events to Handle

| Event Type | Payload | Frontend Action |
| :--- | :--- | :--- |
| `status` | `{message}` | Update connection/progress text. |
| `toc_complete` | `{sections: []}` | Initialize the list of empty sections. |
| `section_token` | `{section_id, content}` | Append text to the specific section. |
| `image` | `{section_id, image_url}` | Render the image banner for that section. |
| `complete` | `{...final_data}` | Show success state, save data, close socket. |
| `error` | `{message}` | Display error toast, stop loading indicator. |
