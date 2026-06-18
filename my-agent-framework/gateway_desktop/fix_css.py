import codecs
import sys

def fix_css():
    file_path = 'src/index.css'
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # The content has mixed encoding. We'll search for the literal '/* Tool Trace Styles */'
        # which might be in UTF-16LE.
        # But wait, looking at the view_file, it looks like it was appended as UTF-16LE.
        # The easiest way is to cut the file at line 467.
        with codecs.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # We know up to line 467 is correct (which is index 466)
        clean_lines = lines[:467]
        
        clean_css = "".join(clean_lines)
        if not clean_css.endswith('\n'):
            clean_css += '\n'
            
        css_to_add = """
/* Tool Trace Styles */
.message-tool-trace-wrapper {
  margin-top: 8px;
  max-width: 100%;
}
.tool-trace-container {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
}
.tool-trace-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
}
.tool-trace-toggle:hover {
  background: var(--hover-color);
}
.trace-zap {
  color: var(--accent-color);
}
.trace-summary-badge {
  margin-left: auto;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}
.badge-ok {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}
.badge-err {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
.tool-trace-list {
  border-top: 1px solid var(--border-color);
}
.tool-trace-entry {
  border-bottom: 1px solid var(--border-color);
}
.tool-trace-entry:last-child {
  border-bottom: none;
}
.trace-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
  text-align: left;
}
.trace-header:hover {
  background: var(--bg-secondary);
}
.trace-icon {
  color: var(--text-secondary);
  display: flex;
  align-items: center;
}
.trace-name {
  font-weight: 600;
}
.trace-duration {
  color: var(--text-secondary);
  font-size: 11px;
}
.trace-badge {
  margin-left: auto;
  font-size: 12px;
}
.trace-body {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.02);
  border-top: 1px dashed var(--border-color);
}
.trace-section {
  margin-bottom: 8px;
}
.trace-section:last-child {
  margin-bottom: 0;
}
.trace-section-label {
  display: block;
  color: var(--text-secondary);
  font-size: 11px;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.trace-code {
  margin: 0;
  padding: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-primary);
}
.trace-code-err {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}
"""
        
        with codecs.open(file_path, 'w', encoding='utf-8') as f:
            f.write(clean_css + css_to_add)
        print("CSS encoding fixed.")
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    fix_css()
