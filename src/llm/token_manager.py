"""
Token Management module
-----------------------
Centralizes Gemini token usage tracking and reporting.
"""

class TokenManager:
    def __init__(self):
        self._last_token_usage = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

    def set_token_usage(self, usage: dict):
        """Set the last token usage and update totals"""
        self._last_token_usage = usage
        if usage:
            self.total_input_tokens += usage.get('input_tokens', 0)
            self.total_output_tokens += usage.get('output_tokens', 0)
            self.total_requests += usage.get('api_requests', 0)

    def get_token_usage(self):
        """Get the last token usage"""
        return self._last_token_usage

    def get_total_token_usage(self):
        """Get total token usage for the session"""
        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_requests': self.total_requests
        }

    def reset_token_usage(self):
        """Reset all token usage counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self._last_token_usage = None
        print("🔄 Token usage counters reset")

    def extract_token_usage(self, response) -> dict:
        """
        Extract token usage info from Gemini API response, if available.
        """
        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "api_requests": 1
        }
        if hasattr(response, "usage_metadata"):
            meta = response.usage_metadata
            usage["input_tokens"] = getattr(meta, "prompt_token_count", 0)
            usage["output_tokens"] = getattr(meta, "candidates_token_count", 0)
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return usage

    def print_token_usage(self):
        usage = self._last_token_usage
        if not usage:
            return
        print("="*60)
        print("📊 GEMINI TOKEN USAGE SUMMARY")
        print("="*60)
        print(f"🔹 Input tokens (prompts):    {usage.get('input_tokens', 0)}")
        print(f"🔹 Output tokens (responses): {usage.get('output_tokens', 0)}")
        print(f"🔹 Total tokens used:         {usage.get('total_tokens', 0)}")
        print(f"🔹 API requests made:         {usage.get('api_requests', 0)}")
        print("="*60)
        if usage.get('total_tokens', 0) < 10000:
            print("💡 Token usage: Light usage - very cost effective")
        print("="*60)

    def print_final_token_summary(self):
        """
        Print a comprehensive token usage summary for the current session.
        This is an alias for print_token_usage for backward compatibility.
        """
        self.print_token_usage()

# Singleton instance for global use
token_manager = TokenManager()
