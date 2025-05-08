from lark import Lark
from lark.lexer import Token
import hashlib
import json

class ParserStateExtractor:
    """
    Extracts consistent parser states from partial sequences using Lark's LALR parser.
    Provides stable state IDs and stack elements that remain consistent between runs.
    """
    
    def __init__(self, grammar_text):
        """
        Initialize with a grammar string
        
        Args:
            grammar_text: The Lark grammar as a string
        """
        # We'll calculate a grammar hash to ensure we detect grammar changes
        self.grammar_hash = hashlib.md5(grammar_text.encode('utf-8')).hexdigest()[:8]
        self.parser = Lark(grammar_text, parser='lalr')
        self._state_mapping = {}  # Map from raw state IDs to consistent state IDs
        self._state_counter = 0

    def get_tokens(self, sequence):
        """Get all tokens from the sequence"""
        lexer = self.parser.lex(sequence)
        return list(lexer)

    def _get_state_fingerprint(self, state_id, parse_table):
        """
        Create a deterministic fingerprint for a state based on its parse table entries
        """
        if state_id not in parse_table.states:
            return None
            
        # Collect actions for this state in a deterministic way
        fingerprint_parts = []
        
        # Add shift/reduce actions
        for term, action_data in parse_table.states.get(state_id, {}).items():
            action_type, target = action_data
            
            # Handle different action types properly
            if hasattr(action_type, '__name__'):
                action_type_name = action_type.__name__
            else:
                # For Action objects that don't have __name__
                action_type_name = action_type.__class__.__name__
            
            # Format based on action type
            if action_type_name == "Shift":
                action = f"{action_type_name}:{target}"
            else:
                # For Reduce and Accept actions
                if hasattr(target, 'origin') and hasattr(target, 'expansion'):
                    action = f"{action_type_name}:{target.origin}:{len(target.expansion)}"
                else:
                    # Fallback for any other action type
                    action = f"{action_type_name}:{str(target)}"
                    
            fingerprint_parts.append((str(term), action))
            
        # Sort for consistency
        fingerprint_parts.sort()
        
        # Return a stable representation
        return tuple(fingerprint_parts)   
    
    def _get_consistent_state_id(self, state_id, parse_table):
        """
        Map a raw state ID to a consistent ID based on its behavior
        """
        # Create fingerprint of the state
        fingerprint = self._get_state_fingerprint(state_id, parse_table)
        if fingerprint is None:
            return None
            
        # Get or create consistent ID for this fingerprint
        fingerprint_hash = hash(fingerprint)
        if fingerprint_hash not in self._state_mapping:
            self._state_mapping[fingerprint_hash] = f"S{self._state_counter}"
            self._state_counter += 1
            
        return self._state_mapping[fingerprint_hash]
    
    def parse_partial(self, sequence, top_k=None, tokens=None):
        """
        Parse a partial sequence and return the parser state and stack
        """
        """char by char
            try:
            # Start interactive parsing
            interactive = self.parser.parse_interactive(sequence)
            
            # Feed tokens one by one to advance the parser
            for token in interactive.lexer_thread.lex(interactive.parser_state):
                interactive.feed_token(token)"""
        try:
            # Use provided tokens or lex the sequence
            if tokens is None:
                tokens = self.get_tokens(sequence)
            
            # Create interactive parser and feed tokens
            interactive = self.parser.parse_interactive('')
            for token in tokens:
                interactive.feed_token(token)
            
            # Now get the parser state after processing the tokens
            parser_state = interactive.parser_state
            parse_table = parser_state.parse_conf.parse_table
            
            # Get raw state information
            raw_state_id = parser_state.position
            raw_stack = list(parser_state.state_stack)
            
            # Get consistent IDs for states
            consistent_state_id = self._get_consistent_state_id(raw_state_id, parse_table)
            consistent_stack = [self._get_consistent_state_id(s, parse_table) for s in raw_stack]
            
            # Prepare result
            result = {
                'current_state': consistent_state_id,
                'stack': consistent_stack if top_k is None else consistent_stack[-top_k:],
                'stack_top': consistent_stack[-1] if consistent_stack else None,
                'success': True,
                'grammar_hash': self.grammar_hash
            }
            
            result['raw_state_id'] = raw_state_id
            result['raw_stack'] = raw_stack
            result['token_history'] = [str(t) for t in interactive.lexer_thread.lex(interactive.parser_state)]
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'success': False,
                'grammar_hash': self.grammar_hash
            }
    def analyze_incremental(self, sequence):
        results = []
        
        try:
            # First, lex the entire string to get tokens
            all_tokens = self.get_tokens(sequence)
            
            # Then parse incrementally token by token
            for i in range(len(all_tokens) + 1):
                # Get parser state after parsing i tokens
                partial_tokens = all_tokens[:i]
                
                # Create an interactive parser
                interactive = self.parser.parse_interactive('')
                
                # Feed tokens one by one
                for token in partial_tokens:
                    interactive.feed_token(token)
                
                # Get parser state
                parser_state = interactive.parser_state
                parse_table = parser_state.parse_conf.parse_table
                
                # Extract state information
                raw_state_id = parser_state.position
                raw_stack = list(parser_state.state_stack)
                
                # Get consistent IDs
                consistent_state_id = self._get_consistent_state_id(raw_state_id, parse_table)
                consistent_stack = [self._get_consistent_state_id(s, parse_table) for s in raw_stack]
                
                # Record token position information
                token_position = 0 if i == 0 else all_tokens[i-1].end_pos
                
                results.append({
                    'position': token_position,
                    'tokens_parsed': i,
                    'text': sequence[:token_position] if token_position > 0 else '',
                    'current_state': consistent_state_id,
                    'stack': consistent_stack,
                    'raw_stack': raw_stack,
                    'success': True
                })
                
        except Exception as e:
            # If we fail at the lexing stage, record the error
            results.append({
                'position': len(sequence),
                'error': str(e),
                'success': False,
                'grammar_hash': self.grammar_hash
            })
            
        return results

    def analyze_incremental_char(self, sequence):
        results = []
        
        # Keep track of how the stack evolves
        state_evolution = []
        
        for i in range(1, len(sequence) + 1):
            partial = sequence[:i]
            result = self.parse_partial(partial)
            
            if result['success']:
                state_evolution.append({
                    'text': partial,
                    'stack': result['stack'].copy() if 'stack' in result else []
                })
                
            results.append({
                'position': i,
                'text': partial,
                **result
            })
        
        # Store evolution for analysis
        self.state_evolution = state_evolution
        
        return results
def extract_parser_states(grammar, sequence, top_k=None):
    
    return extractor.parse_partial(sequence, top_k)

def analyze_sequence(grammar, sequence):
    extractor = ParserStateExtractor(grammar)
    return extractor.analyze_incremental(sequence)

# Example usage
if __name__ == "__main__":

    # Example grammar
    grammar = """
    start: expr
    expr: sum
    sum: product
       | sum "+" product   -> add
       | sum "-" product   -> sub
    product: atom
          | product "*" atom  -> mul
          | product "/" atom  -> div
    atom: NUMBER           -> number
        | "(" expr ")"     -> parens
    
    NUMBER: /\d+/
    
    %import common.WS
    %ignore WS
    """
    json_grammar = r"""
        start: value

        ?value: object
            | array
            | string
            | SIGNED_NUMBER      -> number
            | "true"             -> true
            | "false"            -> false
            | "null"             -> null

        array  : "[" [value ("," value)*] "]"
        object : "{" [pair ("," pair)*] "}"
        pair   : string ":" value

        string : ESCAPED_STRING

        %import common.ESCAPED_STRING
        %import common.SIGNED_NUMBER
        %import common.WS
        %ignore WS
        """
    
    # Test with a partial expression
    sequence = '{"name": "Alexander", "age": 25, "active": true}'
    grammar_path = "./json.ebnf"  # Or any path you want
    with open(grammar_path, "r") as f:
        grammar = f.read()
    grammar = json_grammar
    # Get parser state for the full partial sequence
    print("Parser state for:", sequence)
    extractor = ParserStateExtractor(grammar)
    result = extractor.parse_partial(sequence, top_k=3)
    print(json.dumps(result, indent=2))
    
    # Get incremental analysis
    print("\nIncremental analysis:")
    results = extractor.analyze_incremental(sequence)
    
    for r in results:
        if r['success']:
            print(f"Position {r['position']} ('{r['text']}'): ")
            print(f"  State: {r['current_state']}")
            print(f"  Stack: {r['stack']}")
            print(f"  Raw Stack: {r['raw_stack']}")
        else:
            print(f"Position {r['position']} ('{r['text']}'): Error: {r['error']}")