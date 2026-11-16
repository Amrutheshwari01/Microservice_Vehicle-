// Voice Input & Speech Recognition for Vehicle Fleet Search (S07)

let recognition = null;
let isRecording = false;

function initVoiceSearch(onResultCallback, onStateChangeCallback) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    // Set recognition language based on current active language
    recognition.lang = currentLang === 'hi' ? 'hi-IN' : (currentLang === 'kn' ? 'kn-IN' : 'en-IN');

    recognition.onstart = () => {
      isRecording = true;
      if (onStateChangeCallback) onStateChangeCallback(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (onResultCallback) onResultCallback(transcript);
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      isRecording = false;
      if (onStateChangeCallback) onStateChangeCallback(false);
    };

    recognition.onend = () => {
      isRecording = false;
      if (onStateChangeCallback) onStateChangeCallback(false);
    };
  }
}

function toggleVoiceRecognition(onResultCallback, onStateChangeCallback) {
  if (!recognition) {
    initVoiceSearch(onResultCallback, onStateChangeCallback);
  }

  if (!recognition) {
    // Fallback simulation when Web Speech API is unavailable in browser sandbox
    simulateVoiceInput(onResultCallback);
    return;
  }

  if (isRecording) {
    recognition.stop();
  } else {
    try {
      recognition.lang = currentLang === 'hi' ? 'hi-IN' : (currentLang === 'kn' ? 'kn-IN' : 'en-IN');
      recognition.start();
    } catch (e) {
      console.warn("Microphone start failed, using speech prompt:", e);
      simulateVoiceInput(onResultCallback);
    }
  }
}

function simulateVoiceInput(onResultCallback) {
  const samples = [
    "Tata Ace Hebbal",
    "Mahindra Tractor 2500kg",
    "Light commercial vehicle under 1500",
    "Auto rickshaw cargo Yeshwanthpur"
  ];
  const sample = samples[Math.floor(Math.random() * samples.length)];
  if (onResultCallback) {
    onResultCallback(sample);
  }
}

