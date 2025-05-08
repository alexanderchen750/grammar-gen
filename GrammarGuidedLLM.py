from LLMTokenizer import LLMTokenizer
from ParserStateExtractor import ParserStateExtractor
import json


class GrammarGuidedLLM:
    """Integrates LLM, tokenizers, and parser for grammar-guided generation."""
    
    def __init__(self, grammar_text, llm_tokenizer_name="gpt2", stack_context_length=3, debug=False):
        """Initialize with grammar and tokenizer settings."""
        self.parser_extractor = ParserStateExtractor(grammar_text, )
        self.llm_tokenizer = LLMTokenizer(llm_tokenizer_name)
        self.stack_context_length = stack_context_length
        self.debug = debug

    def log(self, *args):
        if self.debug:
            print("[DEBUG]", *args)

    def process_instance(self, text):
        # Tokenize output with LLM tokenizer
        llm_tokens = self.llm_tokenizer.encode(text)
        
        results = []
        for i in range(len(llm_tokens) - 1):
            # Get prefix tokens and text
            prefix_tokens = llm_tokens[:i+1]
            prefix_text = self.llm_tokenizer.decode(prefix_tokens)
            new_text = self.llm_tokenizer.decode(llm_tokens[i])
            self.log(f"Prefix tokens: {prefix_tokens}")
            self.log(f"Prefix text: {prefix_text}")
            
            result_set = self.parser_extractor.advance_parser(new_text, top_k=self.stack_context_length)
            if i != llm_tokens[-1]:
                result_set['next_token'] = self.llm_tokenizer.decode([llm_tokens[i+1]])
            else:
                result_set['next_token'] = None
            results.append(result_set)
        
        #results = self.parser_extractor.advance_parser(text)
        return results
    
    def process_dataset(self, dataset):
        """Process a set of inputs to create training sets."""
        all_instances = []
        
        for instance in dataset:
            # Validate grammar if needed
            try:
                result = self.process_instance(instance)
                all_instances.append(result)
                self.parser_extractor.reset()
            except Exception:
                print(f"Error processing instance: {instance}")
                continue
        return all_instances
