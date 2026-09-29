"""Business logic, one module per service in the architecture diagram.
Services take a database connection, enforce the rules, and raise
jis.errors exceptions; they know nothing about HTTP."""
