"""Token Management module for Gemini token usage tracking and reporting using TikToken."""
import os, json, tiktoken
from datetime import datetime
from typing import Dict, Any, Optional

class TokenManager:
    def __init__(self):
        self._last_token_usage = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.current_model = None
        
        self.is_batch_mode = False
        self.batch_commands = []
        self.batch_models_used = set()
        
        self.batch_history = []
        self.max_history_size = 50
        self.batch_history_file = os.path.join('static', 'json', 'batch_history.json')
        
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize TikToken encoder: {e}")
            self.encoder = None
        
        self._load_batch_history()

    def _load_batch_history(self):
        """Load batch history from JSON file"""
        try:
            if os.path.exists(self.batch_history_file):
                with open(self.batch_history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.batch_history = data.get('batch_history', [])
                    print(f"📂 Loaded {len(self.batch_history)} batch sessions from history file")
            else:
                print("📂 No existing batch history file found, starting fresh")
        except Exception as e:
            print(f"⚠️ Error loading batch history: {e}")
            self.batch_history = []

    def _save_batch_history(self):
        """Save batch history to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.batch_history_file), exist_ok=True)
            
            data = {
                'batch_history': self.batch_history,
                'last_updated': datetime.now().isoformat(),
                'total_sessions': len(self.batch_history)
            }
            
            with open(self.batch_history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {len(self.batch_history)} batch sessions to history file")
        except Exception as e:
            print(f"❌ Error saving batch history: {e}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string using TikToken"""
        if not self.encoder or not text:
            return 0
            
        try:
            if isinstance(text, dict) or isinstance(text, list):
                text = json.dumps(text, default=str)
            
            tokens = self.encoder.encode(str(text))
            token_count = len(tokens)
            
            if token_count == 0 and text.strip():
                print(f"⚠️ Warning: Zero tokens counted for non-empty text: '{text[:50]}...'")
            elif token_count > 10000:
                print(f"📊 Large token count detected: {token_count:,} tokens for text length {len(str(text))}")
                
            return token_count
        except Exception as e:
            print(f"⚠️ Warning: Token counting failed: {e}")
            fallback_count = len(str(text)) // 4
            print(f"🔄 Using fallback estimation: {fallback_count} tokens")
            return fallback_count

    def track_api_call(self, prompt: str, response: str) -> dict:
        """Track an API call with accurate token counting"""
        input_tokens = self.count_tokens(prompt)
        output_tokens = self.count_tokens(response)
        
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "api_requests": 1,
            "model_name": self.current_model or "unknown"
        }
        
        self.set_token_usage(usage)
        
        if self.is_batch_mode:
            self.batch_commands.append(usage)
            if self.current_model:
                self.batch_models_used.add(self.current_model)
        else:
            self._save_individual_command_session(usage)
        
        print(f"📊 [TOKEN TRACKING] Input: {input_tokens}, Output: {output_tokens}, Total: {usage['total_tokens']}")
        
        return usage

    def _save_individual_command_session(self, usage: dict):
        """Save an individual command as a batch session for tracking purposes"""
        batch_session = {
            'timestamp': datetime.now().isoformat(),
            'commands': 1,
            'total_input_tokens': usage.get('input_tokens', 0),
            'total_output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
            'total_requests': 1,
            'models_used': [usage.get('model_name', 'unknown')],
            'estimated_cost': self._estimate_cost(
                usage.get('input_tokens', 0),
                usage.get('output_tokens', 0),
                usage.get('model_name', 'unknown')
            ),
            'commands_detail': [usage]
        }
        
        self.batch_history.append(batch_session)
        
        if len(self.batch_history) > self.max_history_size:
            self.batch_history = self.batch_history[-self.max_history_size:]
        
        self._save_batch_history()
        print(f"💾 [INDIVIDUAL COMMAND] Saved command session to batch history")

    def set_token_usage(self, usage: dict):
        """Set the last token usage and update totals"""
        self._last_token_usage = usage
        if usage:
            self.total_input_tokens += usage.get('input_tokens', 0)
            self.total_output_tokens += usage.get('output_tokens', 0)
            self.total_requests += usage.get('api_requests', 0)
            
            if self.is_batch_mode:
                command_metric = {
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                    'api_requests': usage.get('api_requests', 0),
                    'model_name': usage.get('model_name') or self.current_model
                }
                self.batch_commands.append(command_metric)
                
                if command_metric['model_name']:
                    self.batch_models_used.add(command_metric['model_name'])

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
        self.is_batch_mode = False
        self.batch_commands = []
        self.batch_models_used = set()
        print("🔄 Token usage counters reset")

    def set_current_model(self, model_name: str):
        """Set the current model being used for accurate pricing"""
        self.current_model = model_name
        print(f"🔧 [MODEL TRACKING] Using model: {model_name}")

    def start_batch_mode(self):
        """Start batch command processing mode"""
        self.is_batch_mode = True
        self.batch_commands = []
        self.batch_models_used = set()
        print("🚀 [BATCH MODE] Started batch command processing")

    def end_batch_mode(self):
        """End batch command processing mode and print summary"""
        if self.is_batch_mode and self.batch_commands:
            self._print_batch_summary()
            
            batch_session = {
                'timestamp': datetime.now().isoformat(),
                'commands': len(self.batch_commands),
                'total_input_tokens': sum(cmd.get('input_tokens', 0) for cmd in self.batch_commands),
                'total_output_tokens': sum(cmd.get('output_tokens', 0) for cmd in self.batch_commands),
                'total_tokens': sum(cmd.get('total_tokens', 0) for cmd in self.batch_commands),
                'total_requests': sum(cmd.get('api_requests', 0) for cmd in self.batch_commands),
                'models_used': list(self.batch_models_used),
                'estimated_cost': sum(
                    self._estimate_cost(
                        cmd.get('input_tokens', 0),
                        cmd.get('output_tokens', 0),
                        cmd.get('model_name', 'unknown')
                    ) for cmd in self.batch_commands
                ),
                'commands_detail': self.batch_commands.copy()
            }
            
            self.batch_history.append(batch_session)
            
            if len(self.batch_history) > self.max_history_size:
                self.batch_history = self.batch_history[-self.max_history_size:]
            
            self._save_batch_history()
        
        self.is_batch_mode = False
        self.batch_commands = []
        self.batch_models_used = set()
        print("🏁 [BATCH MODE] Ended batch command processing")

    def is_in_batch_mode(self) -> bool:
        """Check if currently in batch mode"""
        return self.is_batch_mode

    def is_in_batch_mode(self) -> bool:
        """Check if currently in batch mode"""
        return self.is_batch_mode

    def extract_token_usage(self, response, prompt: str = "", model_name: str = None) -> dict:
        """Extract token usage info using TikToken instead of relying on API metadata."""
        if model_name:
            self.current_model = model_name
            
        response_text = ""
        try:
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        response_text = "".join([part.text for part in content.parts if hasattr(part, 'text')])
                    elif hasattr(content, 'text'):
                        response_text = content.text
                    else:
                        response_text = str(content)
                else:
                    response_text = str(candidate)
            elif hasattr(response, 'result') and response.result:
                result = response.result
                if hasattr(result, 'candidates') and result.candidates:
                    candidate = result.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        response_text = "".join([
                            part.get('text', '') if isinstance(part, dict) else getattr(part, 'text', '')
                            for part in candidate.content.parts
                        ])
            else:
                response_text = str(response)
                
            print(f"[DEBUG] Extracted response text length: {len(response_text)} characters")
            if len(response_text) < 200:
                print(f"[DEBUG] Response text preview: {response_text[:200]}")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not extract response text for token counting: {e}")
            response_text = str(response)
        
        input_tokens = self.count_tokens(prompt) if prompt else 0
        output_tokens = self.count_tokens(response_text)
        
        if model_name:
            self.current_model = model_name
        
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "api_requests": 1,
            "model_name": model_name or self.current_model
        }
        
        self.set_token_usage(usage)
        
        if self.is_batch_mode:
            self.batch_commands.append(usage)
            if self.current_model:
                self.batch_models_used.add(self.current_model)
        else:
            self._save_individual_command_session(usage)
        
        print(f"🔍 [TOKEN EXTRACTION] Prompt tokens: {input_tokens}, Response tokens: {output_tokens}, Total: {usage['total_tokens']}")
        
        return usage

    def print_token_usage(self):
        """Print token usage summary - different behavior for single vs batch commands"""
        usage = self._last_token_usage
        if not usage:
            return
            
        if not self.is_batch_mode:
            print("="*60)
            print("📊 GEMINI TOKEN USAGE SUMMARY")
            print("="*60)
            print(f"🔹 Input tokens (prompts):    {usage.get('input_tokens', 0):,}")
            print(f"🔹 Output tokens (responses): {usage.get('output_tokens', 0):,}")
            print(f"🔹 Total tokens used:         {usage.get('total_tokens', 0):,}")
            print(f"🔹 API requests made:         {usage.get('api_requests', 0)}")
            
            model_used = usage.get('model_name') or self.current_model or 'Unknown'
            print(f"🔹 Model used:                {model_used}")
            
            total_tokens = usage.get('total_tokens', 0)
            estimated_cost = self._estimate_cost(
                usage.get('input_tokens', 0), 
                usage.get('output_tokens', 0), 
                model_used
            )
            print(f"💰 Estimated cost:            ${estimated_cost:.6f}")
            
            print("="*60)
            if total_tokens < 10000:
                print("💡 Token usage: Light usage - very cost effective")
            elif total_tokens < 50000:
                print("💡 Token usage: Moderate usage - reasonable cost")
            else:
                print("💡 Token usage: Heavy usage - consider optimization")
            print("="*60)

    def _print_batch_summary(self):
        """Print comprehensive summary for batch command processing"""
        if not self.batch_commands:
            return
            
        total_input = sum(cmd.get('input_tokens', 0) for cmd in self.batch_commands)
        total_output = sum(cmd.get('output_tokens', 0) for cmd in self.batch_commands)
        total_tokens = total_input + total_output
        total_requests = sum(cmd.get('api_requests', 0) for cmd in self.batch_commands)
        
        total_cost = 0
        model_breakdown = {}
        
        for cmd in self.batch_commands:
            model = cmd.get('model_name', 'Unknown')
            if model not in model_breakdown:
                model_breakdown[model] = {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'requests': 0
                }
            
            model_breakdown[model]['input_tokens'] += cmd.get('input_tokens', 0)
            model_breakdown[model]['output_tokens'] += cmd.get('output_tokens', 0)
            model_breakdown[model]['requests'] += cmd.get('api_requests', 0)
            
            cost = self._estimate_cost(
                cmd.get('input_tokens', 0),
                cmd.get('output_tokens', 0),
                model
            )
            total_cost += cost
        
        print("\n" + "="*70)
        print("📊 BATCH COMMANDS TOKEN USAGE SUMMARY")
        print("="*70)
        print(f"🔹 Total commands processed:  {len(self.batch_commands)}")
        print(f"🔹 Total input tokens:        {total_input:,}")
        print(f"🔹 Total output tokens:       {total_output:,}")
        print(f"🔹 Total tokens used:         {total_tokens:,}")
        print(f"🔹 Total API requests:        {total_requests}")
        print(f"🔹 Average tokens/command:    {total_tokens/len(self.batch_commands):.1f}")
        print(f"💰 Total estimated cost:      ${total_cost:.6f}")
        print("="*70)
        
        if len(model_breakdown) > 1:
            print("🔹 Model breakdown:")
            for model, stats in model_breakdown.items():
                model_cost = self._estimate_cost(
                    stats['input_tokens'],
                    stats['output_tokens'],
                    model
                )
                print(f"   • {model}:")
                print(f"     - Input: {stats['input_tokens']:,}, Output: {stats['output_tokens']:,}")
                print(f"     - Requests: {stats['requests']}, Cost: ${model_cost:.6f}")
        else:
            print(f"🔹 Model used:                {list(self.batch_models_used)[0] if self.batch_models_used else 'Unknown'}")
        
        print("="*70)
        
        if total_tokens < 10000:
            print("💡 Batch usage: Light - very cost effective")
        elif total_tokens < 50000:
            print("💡 Batch usage: Moderate - reasonable cost")
        elif total_tokens < 100000:
            print("💡 Batch usage: Heavy - consider optimization")
        else:
            print("💡 Batch usage: Very heavy - review commands for efficiency")
        print("="*70)

    def get_batch_history(self) -> list:
        """Get the batch history for dashboard display"""
        return self.batch_history.copy()
    
    def get_dashboard_stats(self) -> dict:
        """Get comprehensive statistics for the token usage dashboard"""
        total_batches = len(self.batch_history)
        total_commands = sum(batch.get('commands', 0) for batch in self.batch_history)
        total_tokens_from_batches = sum(batch.get('total_tokens', 0) for batch in self.batch_history)
        total_cost_from_batches = sum(batch.get('estimated_cost', 0) for batch in self.batch_history)
        
        session_summary = self.get_session_summary()
        
        total_tokens = session_summary.get('total_tokens', 0) + total_tokens_from_batches
        total_cost = session_summary.get('estimated_cost', 0) + total_cost_from_batches
        
        total_all_commands = session_summary.get('total_requests', 0) + total_commands
        avg_tokens_per_command = total_tokens / total_all_commands if total_all_commands > 0 else 0
        
        model_usage = {}
        for batch in self.batch_history:
            for model in batch.get('models_used', []):
                if model in model_usage:
                    model_usage[model] += 1
                else:
                    model_usage[model] = 1
        
        current_model = session_summary.get('current_model')
        if current_model and session_summary.get('total_requests', 0) > 0:
            if current_model in model_usage:
                model_usage[current_model] += session_summary.get('total_requests', 0)
            else:
                model_usage[current_model] = session_summary.get('total_requests', 0)
        
        return {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'total_batch_commands': total_batches,
            'avg_tokens_per_command': avg_tokens_per_command,
            'total_input_tokens': session_summary.get('total_input_tokens', 0) + sum(batch.get('total_input_tokens', 0) for batch in self.batch_history),
            'total_output_tokens': session_summary.get('total_output_tokens', 0) + sum(batch.get('total_output_tokens', 0) for batch in self.batch_history),
            'model_usage': model_usage,
            'recent_batches': self.batch_history[-10:] if self.batch_history else []
        }

    def _estimate_cost(self, input_tokens: int, output_tokens: int, model_name: str = None) -> float:
        """Estimate cost based on current Gemini API pricing (July 2025)"""
        if not model_name:
            model_name = self.current_model or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
        
        pricing_table = {
            'gemini-2.5-flash-lite-preview-06-17': {
                'input': 0.10, 'output': 0.40, 'description': 'Flash-Lite Preview'
            },
            'gemini-2.5-flash': {
                'input': 0.30, 'output': 2.50, 'description': 'Flash'
            },
            'gemini-2.5-pro': {
                'input': 1.25, 'output': 10.00, 'description': 'Pro'
            },
            'gemini-2.0-flash': {
                'input': 0.10, 'output': 0.40, 'description': 'Flash 2.0'
            },
            'gemini-2.0-flash-exp': {
                'input': 0.10, 'output': 0.40, 'description': 'Flash 2.0 Experimental'
            },
            'gemini-2.0-flash-thinking-exp-01-21': {
                'input': 0.10, 'output': 0.40, 'description': 'Flash 2.0 Thinking Experimental'
            },
            'gemini-2.0-flash-lite': {
                'input': 0.075, 'output': 0.30, 'description': 'Flash-Lite 2.0'
            },
            'gemini-1.5-flash': {
                'input': 0.075, 'output': 0.30, 'description': 'Flash 1.5 (Deprecated)'
            },
            'gemini-1.5-pro': {
                'input': 1.25, 'output': 5.00, 'description': 'Pro 1.5 (Deprecated)'
            }
        }
        
        model_pricing = pricing_table.get(model_name)
        
        if not model_pricing:
            model_lower = model_name.lower()
            if 'gemini-2.5-flash-lite' in model_lower:
                model_pricing = pricing_table['gemini-2.5-flash-lite-preview-06-17']
            elif 'gemini-2.0-flash-thinking' in model_lower:
                model_pricing = pricing_table['gemini-2.0-flash-thinking-exp-01-21']
            elif 'gemini-2.0-flash-exp' in model_lower:
                model_pricing = pricing_table['gemini-2.0-flash-exp']
            elif 'gemini-2.0-flash-lite' in model_lower:
                model_pricing = pricing_table['gemini-2.0-flash-lite']
            elif 'gemini-2.0-flash' in model_lower:
                model_pricing = pricing_table['gemini-2.0-flash']
            elif 'gemini-2.5-flash' in model_lower:
                model_pricing = pricing_table['gemini-2.5-flash']
            elif 'gemini-2.5-pro' in model_lower:
                model_pricing = pricing_table['gemini-2.5-pro']
            elif 'gemini-1.5-flash' in model_lower:
                model_pricing = pricing_table['gemini-1.5-flash']
            elif 'gemini-1.5-pro' in model_lower:
                model_pricing = pricing_table['gemini-1.5-pro']
            else:
                model_pricing = pricing_table['gemini-2.5-flash-lite-preview-06-17']
                print(f"⚠️ Warning: Unknown model '{model_name}', using Flash-Lite pricing as default")
        
        input_cost = (input_tokens / 1_000_000) * model_pricing['input']
        output_cost = (output_tokens / 1_000_000) * model_pricing['output']
        total_cost = input_cost + output_cost
        
        return total_cost

    def get_session_summary(self) -> dict:
        """Get a comprehensive summary of the current session's token usage"""
        total_usage = self.get_total_token_usage()
        current_model = self.current_model or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite-preview-06-17')
        estimated_cost = self._estimate_cost(
            total_usage['total_input_tokens'], 
            total_usage['total_output_tokens'],
            current_model
        )
        
        return {
            **total_usage,
            'estimated_cost': estimated_cost,
            'current_model': current_model,
            'average_tokens_per_request': (
                total_usage['total_tokens'] / total_usage['total_requests'] 
                if total_usage['total_requests'] > 0 else 0
            )
        }

    def print_final_token_summary(self):
        """Print a comprehensive token usage summary for the current session."""
        summary = self.get_session_summary()
        
        print("\n" + "="*70)
        print("📊 FINAL SESSION TOKEN USAGE SUMMARY")
        print("="*70)
        print(f"🔹 Total input tokens:        {summary['total_input_tokens']:,}")
        print(f"🔹 Total output tokens:       {summary['total_output_tokens']:,}")
        print(f"🔹 Total tokens used:         {summary['total_tokens']:,}")
        print(f"🔹 Total API requests:        {summary['total_requests']}")
        print(f"🔹 Average tokens/request:    {summary['average_tokens_per_request']:.1f}")
        print(f"🔹 Model used:                {summary['current_model']}")
        print(f"💰 Total estimated cost:      ${summary['estimated_cost']:.6f}")
        print("="*70)
        
        total = summary['total_tokens']
        if total < 10000:
            print("💡 Session usage: Light - very cost effective")
        elif total < 50000:
            print("💡 Session usage: Moderate - reasonable cost")
        elif total < 100000:
            print("💡 Session usage: Heavy - consider optimization")
        else:
            print("💡 Session usage: Very heavy - review prompts for efficiency")
        print("="*70)

# Singleton instance for global use
token_manager = TokenManager()
