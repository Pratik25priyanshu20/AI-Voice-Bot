"""Tool definitions for Gemini function calling."""

AVAILABLE_TOOLS = [
    {
        "name": "check_order_status",
        "description": "Check the status of a customer order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "The order number the customer provided",
                }
            },
            "required": ["order_number"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Book an appointment for a customer",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Requested appointment date"},
                "time": {"type": "string", "description": "Requested appointment time"},
            },
            "required": ["date", "time"],
        },
    },
]
