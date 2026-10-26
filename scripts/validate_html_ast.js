#!/usr/bin/env node
/**
 * scripts/validate_html_ast.js
 * 
 * AST Validation Engine CLI & Bridge for UI Sketch-to-Code Converter (Week 6: COM71123-8).
 * Integrates html-validate to check structural integrity, syntax, and element hierarchy
 * of generated HTML snippets and complete documents.
 */

const fs = require('fs');
const path = require('path');
const { HtmlValidate } = require('html-validate');

// Severity mapping from html-validate numeric constants
const SEVERITY_NAMES = {
  1: 'warning',
  2: 'error'
};

function loadConfig(customConfigPath) {
  const candidatePaths = [
    customConfigPath,
    path.resolve(process.cwd(), '.htmlvalidate.json'),
    path.resolve(__dirname, '..', '.htmlvalidate.json')
  ].filter(Boolean);

  for (const cfgPath of candidatePaths) {
    if (fs.existsSync(cfgPath)) {
      try {
        const raw = fs.readFileSync(cfgPath, 'utf-8');
        return JSON.parse(raw);
      } catch (err) {
        console.error(`[WARN] Failed to parse config at ${cfgPath}: ${err.message}`);
      }
    }
  }

  // Sensible default configuration if no config file is found
  return {
    extends: ['html-validate:recommended'],
    rules: {
      'close-order': 'error',
      'no-dup-id': 'error',
      'void-content': 'error',
      'element-required-attributes': 'error',
      'no-unknown-elements': 'error',
      'no-implicit-close': 'warn',
      'no-redundant-role': 'warn',
      'no-trailing-whitespace': 'off',
      'void-style': 'off',
      'no-inline-style': 'off',
      'require-sri': 'off',
      'attribute-boolean-style': 'off',
      'doctype-html': 'off'
    }
  };
}

function normalizeMessages(results) {
  const errors = [];
  const warnings = [];

  for (const res of results) {
    for (const msg of res.messages || []) {
      const entry = {
        ruleId: msg.ruleId,
        severity: SEVERITY_NAMES[msg.severity] || (msg.severity === 2 ? 'error' : 'warning'),
        message: msg.message,
        line: msg.line,
        column: msg.column,
        offset: msg.offset,
        size: msg.size,
        selector: msg.selector || null,
        ruleUrl: msg.ruleUrl || null
      };

      if (entry.severity === 'error') {
        errors.push(entry);
      } else {
        warnings.push(entry);
      }
    }
  }

  return { errors, warnings };
}

function runValidation(htmlContent, config) {
  const validator = new HtmlValidate(config);
  const report = validator.validateStringSync(htmlContent);

  const { errors, warnings } = normalizeMessages(report.results || []);

  return {
    valid: report.valid,
    errorCount: report.errorCount || errors.length,
    warningCount: report.warningCount || warnings.length,
    errors,
    warnings
  };
}

async function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', err => reject(err));
  });
}

async function main() {
  const args = process.argv.slice(2);
  let htmlInput = null;
  let customConfigPath = null;
  let prettyOutput = false;
  let isSnippet = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--stdin') {
      htmlInput = await readStdin();
    } else if (arg === '--html' && i + 1 < args.length) {
      htmlInput = args[++i];
    } else if (arg === '--config' && i + 1 < args.length) {
      customConfigPath = args[++i];
    } else if (arg === '--pretty') {
      prettyOutput = true;
    } else if (arg === '--snippet') {
      isSnippet = true;
    } else if (arg === '--help' || arg === '-h') {
      console.log('Usage: node scripts/validate_html_ast.js [options] [filePath]');
      console.log('Options:');
      console.log('  --html <string>     Validate HTML string');
      console.log('  --stdin             Read HTML from standard input');
      console.log('  --config <path>     Path to custom .htmlvalidate.json');
      console.log('  --pretty            Format output for terminal');
      console.log('  --snippet           Treat as HTML snippet (doctype checks disabled)');
      process.exit(0);
    } else if (!arg.startsWith('--') && !htmlInput) {
      // Treat as file path
      const resolved = path.resolve(arg);
      if (fs.existsSync(resolved)) {
        htmlInput = fs.readFileSync(resolved, 'utf-8');
      } else {
        console.error(JSON.stringify({
          valid: false,
          errorCount: 1,
          warningCount: 0,
          errors: [{ ruleId: 'file-not-found', severity: 'error', message: `File not found: ${arg}`, line: 0, column: 0 }],
          warnings: []
        }));
        process.exit(2);
      }
    }
  }

  if (htmlInput === null) {
    // If no argument, attempt to read stdin
    if (!process.stdin.isTTY) {
      htmlInput = await readStdin();
    } else {
      console.error(JSON.stringify({
        valid: false,
        errorCount: 1,
        warningCount: 0,
        errors: [{ ruleId: 'no-input', severity: 'error', message: 'No HTML input provided via arguments, file, or stdin', line: 0, column: 0 }],
        warnings: []
      }));
      process.exit(2);
    }
  }

  const config = loadConfig(customConfigPath);
  if (isSnippet) {
    config.rules = Object.assign({}, config.rules, {
      'doctype-html': 'off',
      'element-required-ancestor': 'off'
    });
  }

  const result = runValidation(htmlInput, config);

  if (prettyOutput) {
    console.log('====================================================');
    console.log('       HTML AST Structural Validation Report        ');
    console.log('====================================================');
    console.log(`Status:  ${result.valid ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`Errors:  ${result.errorCount}`);
    console.log(`Warnings: ${result.warningCount}`);
    console.log('----------------------------------------------------');

    if (result.errors.length > 0) {
      console.log('\n[ERRORS]:');
      result.errors.forEach((err, idx) => {
        console.log(`  ${idx + 1}. [${err.ruleId}] Line ${err.line}, Col ${err.column}: ${err.message}`);
        if (err.selector) console.log(`     Target: ${err.selector}`);
      });
    }

    if (result.warnings.length > 0) {
      console.log('\n[WARNINGS]:');
      result.warnings.forEach((warn, idx) => {
        console.log(`  ${idx + 1}. [${warn.ruleId}] Line ${warn.line}, Col ${warn.column}: ${warn.message}`);
        if (warn.selector) console.log(`     Target: ${warn.selector}`);
      });
    }

    console.log('====================================================');
  } else {
    console.log(JSON.stringify(result, null, 2));
  }

  process.exit(result.valid ? 0 : 1);
}

if (require.main === module) {
  main().catch(err => {
    console.error(JSON.stringify({
      valid: false,
      errorCount: 1,
      warningCount: 0,
      errors: [{ ruleId: 'internal-error', severity: 'error', message: err.message, line: 0, column: 0 }],
      warnings: []
    }));
    process.exit(2);
  });
}

module.exports = {
  loadConfig,
  normalizeMessages,
  runValidation
};
