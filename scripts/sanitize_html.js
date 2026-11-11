#!/usr/bin/env node
/**
 * scripts/sanitize_html.js
 * 
 * DOMPurify Security Sanitization Bridge for UI Sketch-to-Code Converter (Week 10: COM71123-12).
 * Integrates DOMPurify and JSDOM to defang XSS vectors, remove malicious scripts/event handlers,
 * and validate safe HTML rendering.
 */

const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

// Initialize JSDOM environment for DOMPurify
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.Node = dom.window.Node;

const createDOMPurify = require('dompurify');
const DOMPurify = createDOMPurify(dom.window);

// Default permissive yet secure configuration tailored for Tailwind CSS & HTML5
const PURIFY_CONFIG = {
  WHOLE_DOCUMENT: true,
  RETURN_DOM: false,
  RETURN_DOM_FRAGMENT: false,
  RETURN_TRUSTED_TYPE: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
  FORBID_TAGS: ['script', 'object', 'embed', 'applet', 'base'],
  FORBID_ATTR: [
    'onerror', 'onload', 'onclick', 'onmouseover', 'onmouseout',
    'onfocus', 'onblur', 'onkeydown', 'onkeypress', 'onkeyup',
    'onsubmit', 'onreset', 'onchange', 'formaction'
  ],
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  ADD_TAGS: ['nav', 'header', 'main', 'section', 'article', 'aside', 'footer', 'figure', 'figcaption', 'style', 'link', 'meta', 'title'],
  ADD_ATTR: ['target', 'role', 'aria-label', 'aria-labelledby', 'aria-describedby', 'aria-hidden', 'aria-required', 'rel', 'href', 'crossorigin', 'name', 'content', 'charset']
};

function sanitizeHTML(rawHtml, options = {}) {
  const config = { ...PURIFY_CONFIG, ...options };
  const strippedTags = [];
  const strippedAttrs = [];

  // Track what DOMPurify removes using hooks
  DOMPurify.addHook('beforeSanitizeElements', (node) => {
    if (node.tagName && config.FORBID_TAGS.includes(node.tagName.toLowerCase())) {
      // Do not count trusted Tailwind CDN script as a malicious threat
      if (node.tagName.toLowerCase() === 'script' && node.src && node.src.includes('cdn.tailwindcss.com')) {
        return;
      }
      strippedTags.push(node.tagName.toLowerCase());
    }
  });

  DOMPurify.addHook('beforeSanitizeAttributes', (node) => {
    if (node.attributes) {
      for (let i = 0; i < node.attributes.length; i++) {
        const attrName = node.attributes[i].name.toLowerCase();
        const attrVal = node.attributes[i].value;
        if (config.FORBID_ATTR.includes(attrName) || attrVal.toLowerCase().startsWith('javascript:')) {
          strippedAttrs.push({ tag: node.tagName.toLowerCase(), attribute: attrName, value: attrVal });
        }
      }
    }
  });

  let clean = DOMPurify.sanitize(rawHtml, config);
  DOMPurify.removeAllHooks();

  // Ensure trusted Tailwind CSS runtime & fonts are preserved for safe previewing
  if (rawHtml.includes('https://cdn.tailwindcss.com') && !clean.includes('https://cdn.tailwindcss.com')) {
    if (clean.includes('</head>')) {
      clean = clean.replace('</head>', '  <script src="https://cdn.tailwindcss.com"></script>\n</head>');
    } else if (clean.includes('<body')) {
      clean = clean.replace('<body', '<script src="https://cdn.tailwindcss.com"></script>\n<body');
    }
  }

  return {
    clean_html: clean,
    threats_detected: strippedTags.length + strippedAttrs.length,
    stripped_tags: strippedTags,
    stripped_attributes: strippedAttrs
  };
}

// CLI Support: node scripts/sanitize_html.js <input_path_or_json>
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    // Read from standard input
    let inputData = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', chunk => { inputData += chunk; });
    process.stdin.on('end', () => {
      const result = sanitizeHTML(inputData);
      process.stdout.write(JSON.stringify(result));
    });
  } else {
    const filePath = path.resolve(process.cwd(), args[0]);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      const result = sanitizeHTML(content);
      process.stdout.write(JSON.stringify(result, null, 2));
    } else {
      console.error(`[ERROR] File not found: ${filePath}`);
      process.exit(1);
    }
  }
}

module.exports = { sanitizeHTML, PURIFY_CONFIG };
