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

        lexer_tokens = self.parser_extractor.get_lexical_tokens_with_positions(text)
        print("Lexer tokens: ", lexer_tokens)

        results = []
        for i in range(len(llm_tokens) - 1):
            new_text = self.llm_tokenizer.decode(llm_tokens[i])
            self.log(f"Prefix tokens: {llm_tokens[:i+1]}")
            self.log(f"Prefix text: {self.llm_tokenizer.decode(llm_tokens[:i+1])}")
            print(f"Prefix text: {new_text}")
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
            except Exception as e:
                #print(f"Error processing instance: {instance}")
                print("Error: ", str(e))
                continue
        return all_instances
