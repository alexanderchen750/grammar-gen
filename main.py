from GrammarGuidedLLM import GrammarGuidedLLM
import json

def main():
    # File paths - manually change these as needed
    grammar_file = "grammar.lark"
    dataset_file = "dataset.json"
    output_file = "results.json"

    # Fallback dataset if the file can't be opened
    
    
    # Read grammar from file
    with open(grammar_file, 'r') as f:
        grammar = f.read()

  
    
    # Read dataset from file
    with open(dataset_file, 'r') as f:
        dataset = json.load(f)
        # Ensure dataset is a list
        if not isinstance(dataset, list):
            dataset = [dataset]
    dataset = [json.dumps(example) for example in dataset]
    # Initialize parser
    builder = GrammarGuidedLLM(
        grammar_text=grammar, 
        llm_tokenizer_name="gpt2", 
        stack_context_length=3, 
    )
    
    # Process dataset
    print(f"Processing {len(dataset)} examples...")
    results = builder.process_dataset(dataset)
    
    # Write results to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()