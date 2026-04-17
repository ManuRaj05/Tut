import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2';

// Skip local checks so it pulls the model directly from HF hub
env.allowLocalModels = false;

class CodeAssistant {
    static task = 'text-generation';
    static model = 'Xenova/tinycodes-1M';
    static instance = null;

    static async getInstance(progress_callback = null) {
        if (this.instance === null) {
            this.instance = await pipeline(this.task, this.model, { progress_callback });
        }
        return this.instance;
    }
}

// Listen for messages from the PairCodingPanel
self.addEventListener('message', async (event) => {
    // text should contain the editor's cursor prefix
    const { id, text, max_new_tokens = 20 } = event.data;

    // Optional: Warm up on load
    if (event.data.type === 'load') {
        self.postMessage({ status: 'progress', data: { file: 'model', status: 'loading' } });
        await CodeAssistant.getInstance(x => {
            self.postMessage({ status: 'progress', data: x });
        });
        self.postMessage({ status: 'ready' });
        return;
    }

    if (!text) return;

    try {
        const generator = await CodeAssistant.getInstance();

        // Compute response
        const output = await generator(text, { 
            max_new_tokens: max_new_tokens,
            temperature: 0.2, // low temperature for code completion
            do_sample: false
        });
        
        let generatedText = output[0].generated_text;
        
        // The output usually contains the prompt + generated part. 
        // We only want the newly hallucinated substring.
        if (generatedText.startsWith(text)) {
            generatedText = generatedText.substring(text.length);
        }

        self.postMessage({ status: 'complete', id, output: generatedText });
    } catch (err) {
        self.postMessage({ status: 'error', id, error: err.message });
    }
});
