"""Centralized, code-task-optimized prompts (application layer).

Prompts are part of use-case logic, so they live in the application layer (not
infrastructure) to respect the dependency rule. They are written for any capable
code-specialized instruct model: terse, role-framed, grounded strictly in
provided source, and — for JSON tasks — explicit that only schema-conforming
JSON should be returned. Repository content is always passed through
``wrap_untrusted`` by the caller (prompt-injection defense).
"""
