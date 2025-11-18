# MCP Content Types and Cursor Rendering Support

## Available MCP Content Types

MCP tools can return the following content types:

### 1. **TextContent** ✅
- **Fields:**
  - `type`: `"text"` (required)
  - `text`: `str` (required) - The text content
  - `annotations`: Optional metadata
  - `meta`: Optional metadata
- **Usage:** Plain text, markdown, code blocks
- **Cursor Support:** ✅ **Fully Supported**
  - Renders markdown (headers, lists, tables, code blocks)
  - Does **NOT** render Mermaid diagrams in code blocks (shows as text only)
  - Supports HTML tags (limited)

### 2. **ImageContent** ✅
- **Fields:**
  - `type`: `"image"` (required)
  - `data`: `str` (required) - Base64-encoded image data
  - `mimeType`: `str` (required) - e.g., `"image/png"`, `"image/jpeg"`, `"image/svg+xml"`
  - `annotations`: Optional metadata
  - `meta`: Optional metadata
- **Usage:** PNG, JPEG, SVG images
- **Cursor Support:** ✅ **Fully Supported**
  - Renders images directly in chat
  - Supports PNG, JPEG formats
  - SVG support may vary

### 3. **AudioContent** ❓
- **Fields:**
  - `type`: `"audio"` (required)
  - `data`: `str` (required) - Base64-encoded audio data
  - `mimeType`: `str` (required) - e.g., `"audio/mpeg"`, `"audio/wav"`
  - `annotations`: Optional metadata
  - `meta`: Optional metadata
- **Usage:** MP3, WAV audio files
- **Cursor Support:** ❓ **Unknown/Unsupported**
  - Not commonly used in MCP tools
  - May not render in Cursor chat interface

## Tool Response Format

MCP tools return a **list** of content items:

```python
from mcp.types import TextContent, ImageContent

# Tool handler returns a list
def handle_tool(...) -> List[Union[TextContent, ImageContent]]:
    contents = []
    
    # Add text content
    contents.append(TextContent(
        type="text",
        text="# Hello\n\nThis is **markdown** text."
    ))
    
    # Add image content
    contents.append(ImageContent(
        type="image",
        data=base64_image_data,
        mimeType="image/png"
    ))
    
    return contents
```

## What Cursor Can Render

### ✅ **Supported:**
1. **Markdown Text** - Headers, lists, tables, code blocks, links
2. **Images** - PNG, JPEG (via `ImageContent`)
3. **Code Blocks** - Syntax highlighting for most languages
4. **Tables** - Markdown tables render nicely

### ❌ **Not Supported:**
1. **Mermaid Diagrams** - Shows as text code blocks, not rendered diagrams
2. **Interactive Elements** - No JavaScript execution
3. **Complex HTML** - Limited HTML support
4. **SVG** - May not render (use PNG instead)

## Best Practices

### For Network Maps / Diagrams:
1. **Primary:** Use `ImageContent` with PNG (high resolution, 2400px width)
2. **Secondary:** Include `TextContent` with Mermaid code for copying/export
3. **Fallback:** Always provide PNG since Mermaid doesn't render

### For Text Responses:
1. Use markdown for formatting
2. Use code blocks for code snippets
3. Use tables for structured data
4. Keep text concise and well-formatted

### For Images:
1. Use PNG format for best compatibility
2. Use base64 encoding
3. Specify correct `mimeType`
4. Consider resolution (2400px width for detailed images)

## Example: Network Map Tool

```python
def create_network_map(...):
    # Generate Mermaid diagram
    mermaid_diagram = generate_mermaid(...)
    
    # Convert to PNG
    png_base64 = convert_mermaid_to_png(mermaid_diagram)
    
    contents = []
    
    # 1. PNG image (primary - actually renders)
    if png_base64:
        contents.append(ImageContent(
            type="image",
            data=png_base64,
            mimeType="image/png"
        ))
    
    # 2. Mermaid text (secondary - for copying)
    contents.append(TextContent(
        type="text",
        text=f"```mermaid\n{mermaid_diagram}\n```"
    ))
    
    # 3. Summary text
    contents.append(TextContent(
        type="text",
        text="**Summary:** 8 devices online"
    ))
    
    return contents
```

## Summary

| Content Type | MCP Support | Cursor Rendering | Best Use Case |
|-------------|-------------|------------------|---------------|
| `TextContent` (markdown) | ✅ | ✅ Full | Text, tables, code |
| `TextContent` (Mermaid) | ✅ | ❌ Text only | Copy/export diagrams |
| `ImageContent` (PNG) | ✅ | ✅ Full | Diagrams, screenshots |
| `ImageContent` (SVG) | ✅ | ❓ Limited | May not render |
| `AudioContent` | ✅ | ❓ Unknown | Audio playback |

**Recommendation:** For visual content, always use `ImageContent` with PNG format. Include Mermaid/other source code as `TextContent` for users who want to copy or export it.

