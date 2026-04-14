"""
Key Predictor and Word Suggestion Engine for Gesture Control Keyboard
=====================================================================
Provides intelligent word prediction, auto-correction, and learning capabilities
for the virtual keyboard system.
"""

import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime
import threading
import pickle

# ============================================================================
# Common Words Dictionary (Base vocabulary)
# ============================================================================

BASE_WORDS = {
    # Most common English words
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
    
    # Technology related
    'computer', 'keyboard', 'mouse', 'click', 'scroll', 'gesture', 'control',
    'virtual', 'typing', 'screen', 'cursor', 'button', 'window', 'file',
    'folder', 'document', 'program', 'application', 'browser', 'internet',
    
    # Common actions
    'open', 'close', 'save', 'delete', 'copy', 'paste', 'cut', 'undo', 'redo',
    'select', 'deselect', 'move', 'resize', 'minimize', 'maximize', 'exit',
    
    # Greetings and common phrases
    'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening', 'night',
    'please', 'thank', 'thanks', 'sorry', 'welcome', 'yes', 'no', 'maybe',
    
    # Gesture control specific
    'gesture', 'hand', 'finger', 'palm', 'fist', 'pinch', 'peace', 'point',
    'zoom', 'screenshot', 'volume', 'brightness', 'play', 'pause', 'stop',
}

# ============================================================================
# Common Word Pairs (Bigrams) for context prediction
# ============================================================================

COMMON_BIGRAMS = {
    ('thank', 'you'), ('how', 'are'), ('i', 'am'), ('i', 'have'),
    ('i', 'will'), ('i', 'would'), ('would', 'like'), ('want', 'to'),
    ('need', 'to'), ('going', 'to'), ('have', 'to'), ('able', 'to'),
    ('looking', 'for'), ('waiting', 'for'), ('ask', 'for'), ('pay', 'for'),
    ('good', 'morning'), ('good', 'afternoon'), ('good', 'evening'), ('good', 'night'),
    ('hello', 'there'), ('hi', 'there'), ('see', 'you'), ('take', 'care'),
    ('no', 'problem'), ('no', 'worries'), ('no', 'way'), ('of', 'course'),
    ('as', 'well'), ('as', 'soon'), ('as', 'possible'), ('as', 'if'),
    ('gesture', 'control'), ('virtual', 'keyboard'), ('hand', 'gesture'),
    ('mouse', 'click'), ('right', 'click'), ('left', 'click'), ('double', 'click'),
}

# ============================================================================
# Correction Rules for common typos
# ============================================================================

CORRECTION_RULES = {
    # Common finger placement errors
    'teh': 'the', 'adn': 'and', 'iwll': 'will', 'withe': 'with',
    'whta': 'what', 'thsi': 'this', 'frmo': 'from', 'hte': 'the',
    'yuo': 'you', 'yuor': 'your', 'thier': 'their', 'recieve': 'receive',
    
    # Missing letters
    'wnt': 'want', 'gng': 'going', 'cmng': 'coming', 'tlk': 'talk',
    'wrk': 'work', 'pls': 'please', 'thx': 'thanks', 'sry': 'sorry',
    
    # Extra letters
    'thee': 'the', 'andd': 'and', 'wlll': 'will', 'thiss': 'this',
    'youu': 'you', 'goood': 'good', 'helllo': 'hello', 'thankks': 'thanks',
}

# ============================================================================
# Key Proximity Map for typo correction (QWERTY layout)
# ============================================================================

KEY_PROXIMITY = {
    # Row 1
    'q': ['w', 'a', 's', '1', '2'],
    'w': ['q', 'e', 'a', 's', 'd', '2', '3'],
    'e': ['w', 'r', 's', 'd', 'f', '3', '4'],
    'r': ['e', 't', 'd', 'f', 'g', '4', '5'],
    't': ['r', 'y', 'f', 'g', 'h', '5', '6'],
    'y': ['t', 'u', 'g', 'h', 'j', '6', '7'],
    'u': ['y', 'i', 'h', 'j', 'k', '7', '8'],
    'i': ['u', 'o', 'j', 'k', 'l', '8', '9'],
    'o': ['i', 'p', 'k', 'l', '9', '0'],
    'p': ['o', 'l', '0', '-'],
    
    # Row 2
    'a': ['q', 'w', 's', 'z', 'x', '1'],
    's': ['w', 'e', 'a', 'd', 'z', 'x', 'c', '2'],
    'd': ['e', 'r', 's', 'f', 'x', 'c', 'v', '3'],
    'f': ['r', 't', 'd', 'g', 'c', 'v', 'b', '4'],
    'g': ['t', 'y', 'f', 'h', 'v', 'b', 'n', '5'],
    'h': ['y', 'u', 'g', 'j', 'b', 'n', 'm', '6'],
    'j': ['u', 'i', 'h', 'k', 'n', 'm', '7'],
    'k': ['i', 'o', 'j', 'l', 'm', '8'],
    'l': ['o', 'p', 'k', '9'],
    
    # Row 3
    'z': ['a', 's', 'x'],
    'x': ['a', 's', 'z', 'c', 'd'],
    'c': ['s', 'd', 'x', 'v', 'f'],
    'v': ['d', 'f', 'c', 'b', 'g'],
    'b': ['f', 'g', 'v', 'n', 'h'],
    'n': ['g', 'h', 'b', 'm', 'j'],
    'm': ['h', 'j', 'n', 'k'],
    
    # Numbers
    '1': ['q', 'w', '2'],
    '2': ['q', 'w', '1', '3'],
    '3': ['w', 'e', '2', '4'],
    '4': ['e', 'r', '3', '5'],
    '5': ['r', 't', '4', '6'],
    '6': ['t', 'y', '5', '7'],
    '7': ['y', 'u', '6', '8'],
    '8': ['u', 'i', '7', '9'],
    '9': ['i', 'o', '8', '0'],
    '0': ['o', 'p', '9', '-'],
}

# ============================================================================
# Word Predictor Class
# ============================================================================

class KeyPredictor:
    """Intelligent word prediction and auto-correction engine"""
    
    def __init__(self, user_data_file='user_dictionary.json'):
        """
        Initialize the predictor with base vocabulary
        
        Args:
            user_data_file: Path to store user-specific word data
        """
        self.user_data_file = user_data_file
        self.word_frequency = Counter()
        self.word_pairs = defaultdict(Counter)  # For context prediction
        self.user_words = set()  # Words added by user
        self.word_scores = {}  # Cached scores for words
        
        # Thread lock for concurrent access
        self.lock = threading.Lock()
        
        # Load base vocabulary
        self._load_base_vocabulary()
        
        # Load user data if exists
        self._load_user_data()
        
        # Load common word pairs
        self._load_common_pairs()
        
        print(f"[PREDICTOR] Initialized with {len(self.word_frequency)} words")
    
    def _load_base_vocabulary(self):
        """Load base vocabulary with initial frequencies"""
        # Base words with higher frequency for common words
        for i, word in enumerate(BASE_WORDS):
            # More common words get higher initial frequency
            frequency = 100 - (i // 10) if i < 100 else 10
            self.word_frequency[word.lower()] = frequency
        
        # Add special gesture-related words with higher priority
        gesture_words = ['gesture', 'control', 'virtual', 'keyboard', 'click', 'scroll']
        for word in gesture_words:
            self.word_frequency[word] = 150
    
    def _load_common_pairs(self):
        """Load common word pairs for context prediction"""
        for pair in COMMON_BIGRAMS:
            word1, word2 = pair
            self.word_pairs[word1][word2] += 10  # Initial weight
    
    def _load_user_data(self):
        """Load user-specific word data from file"""
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.word_frequency.update(data.get('frequencies', {}))
                    self.user_words.update(data.get('user_words', []))
                    # Load word pairs
                    for w1, pairs in data.get('pairs', {}).items():
                        for w2, count in pairs.items():
                            self.word_pairs[w1][w2] += count
                print(f"[PREDICTOR] Loaded user data from {self.user_data_file}")
            except Exception as e:
                print(f"[PREDICTOR] Error loading user data: {e}")
    
    def _save_user_data(self):
        """Save user-specific word data to file"""
        try:
            data = {
                'frequencies': dict(self.word_frequency),
                'user_words': list(self.user_words),
                'pairs': {w1: dict(pairs) for w1, pairs in self.word_pairs.items()},
                'last_updated': datetime.now().isoformat()
            }
            with open(self.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[PREDICTOR] Error saving user data: {e}")
    
    def add_word(self, word):
        """
        Add a word to the vocabulary and increase its frequency
        
        Args:
            word: Word to add or reinforce
        """
        with self.lock:
            word_lower = word.lower()
            self.word_frequency[word_lower] += 1
            self.user_words.add(word_lower)
            # Clear cached scores
            if word_lower in self.word_scores:
                del self.word_scores[word_lower]
            # Auto-save periodically
            self._save_user_data()
    
    def add_word_pair(self, word1, word2):
        """
        Record a word pair for context prediction
        
        Args:
            word1: Previous word
            word2: Current word
        """
        with self.lock:
            self.word_pairs[word1.lower()][word2.lower()] += 1
            self._save_user_data()
    
    def _calculate_score(self, word, context=None):
        """
        Calculate prediction score for a word
        
        Args:
            word: Word to score
            context: Previous word for context scoring
        
        Returns:
            float: Score for the word
        """
        word_lower = word.lower()
        
        # Base frequency score
        frequency_score = self.word_frequency.get(word_lower, 0)
        
        # Context score (if previous word provided)
        context_score = 0
        if context and context in self.word_pairs:
            context_score = self.word_pairs[context].get(word_lower, 0) * 5
        
        # Length bonus (shorter words slightly favored)
        length_bonus = max(0, (10 - len(word)) * 2)
        
        # Recency bonus (not implemented in this version)
        recency_bonus = 0
        
        total_score = frequency_score + context_score + length_bonus + recency_bonus
        
        return total_score
    
    def predict(self, current_word, previous_word=None, max_suggestions=5):
        """
        Predict word completions and suggestions
        
        Args:
            current_word: Partial word being typed
            previous_word: Previous word for context
            max_suggestions: Number of suggestions to return
        
        Returns:
            list: Sorted list of word suggestions
        """
        if not current_word:
            # No current word, suggest common words based on context
            return self._suggest_next_words(previous_word, max_suggestions)
        
        current_lower = current_word.lower()
        matches = []
        
        with self.lock:
            for word, freq in self.word_frequency.items():
                # Check if word starts with current input
                if word.startswith(current_lower):
                    score = self._calculate_score(word, previous_word)
                    matches.append((word, score))
            
            # Sort by score (higher is better)
            matches.sort(key=lambda x: x[1], reverse=True)
            
            # Return top matches
            suggestions = [word for word, score in matches[:max_suggestions]]
            
            # If no matches, try to correct
            if not suggestions:
                corrected = self.correct_word(current_word)
                if corrected and corrected != current_word:
                    suggestions = [corrected] + self._suggest_next_words(previous_word, max_suggestions-1)
            
            return suggestions
    
    def _suggest_next_words(self, previous_word, max_suggestions=5):
        """Suggest next words based on previous word context"""
        if not previous_word:
            # No context, return most common words
            common_words = [word for word, _ in self.word_frequency.most_common(max_suggestions)]
            return common_words
        
        previous_lower = previous_word.lower()
        
        if previous_lower in self.word_pairs:
            # Get most common next words
            next_words = self.word_pairs[previous_lower].most_common(max_suggestions)
            return [word for word, _ in next_words]
        
        return []
    
    def correct_word(self, word):
        """
        Auto-correct a misspelled word
        
        Args:
            word: Potentially misspelled word
        
        Returns:
            str: Corrected word or original if no correction found
        """
        word_lower = word.lower()
        
        # Check direct correction rules
        if word_lower in CORRECTION_RULES:
            return CORRECTION_RULES[word_lower]
        
        # Check if word is already in dictionary
        if word_lower in self.word_frequency:
            return word
        
        # Try to find similar words
        best_match = None
        best_score = 0
        
        with self.lock:
            for dict_word in self.word_frequency:
                # Calculate similarity score
                score = self._calculate_similarity(word_lower, dict_word)
                if score > best_score and score > 0.7:  # 70% similarity threshold
                    best_score = score
                    best_match = dict_word
        
        return best_match if best_match else word
    
    def _calculate_similarity(self, word1, word2):
        """
        Calculate similarity between two words using Levenshtein distance
        and keyboard proximity
        
        Args:
            word1: First word
            word2: Second word
        
        Returns:
            float: Similarity score (0-1)
        """
        if word1 == word2:
            return 1.0
        
        # Length difference penalty
        len_diff = abs(len(word1) - len(word2))
        if len_diff > 2:
            return 0.0
        
        # Calculate character-by-character similarity
        matches = 0
        total = max(len(word1), len(word2))
        
        for i, char1 in enumerate(word1):
            if i < len(word2):
                if char1 == word2[i]:
                    matches += 1
                elif char1 in KEY_PROXIMITY and word2[i] in KEY_PROXIMITY.get(char1, []):
                    # Keyboard proximity match
                    matches += 0.7
        
        base_similarity = matches / total
        
        # Check for common substitutions
        if base_similarity > 0.6:
            return base_similarity
        
        return 0.0
    
    def learn_from_text(self, text):
        """
        Learn from user's typed text to improve predictions
        
        Args:
            text: Text that was typed
        """
        # Split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        with self.lock:
            for i, word in enumerate(words):
                # Add word to vocabulary
                self.word_frequency[word] += 1
                
                # Record word pair
                if i > 0:
                    prev_word = words[i-1]
                    self.word_pairs[prev_word][word] += 1
                
                # Add to user words
                if len(word) > 2:  # Only remember meaningful words
                    self.user_words.add(word)
            
            # Clear cached scores for updated words
            for word in words:
                if word in self.word_scores:
                    del self.word_scores[word]
        
        # Save updated data
        self._save_user_data()
    
    def get_common_words(self, limit=50):
        """
        Get most common words from vocabulary
        
        Args:
            limit: Maximum number of words to return
        
        Returns:
            list: Most common words
        """
        with self.lock:
            return [word for word, _ in self.word_frequency.most_common(limit)]
    
    def get_user_words(self):
        """Get words added by the user"""
        with self.lock:
            return list(self.user_words)
    
    def get_word_frequency(self, word):
        """Get frequency of a specific word"""
        with self.lock:
            return self.word_frequency.get(word.lower(), 0)
    
 def reset_to_default(self):
        """Reset predictor to default vocabulary"""
        with self.lock:
            self.word_frequency.clear()
            self.word_pairs.clear()
            self.user_words.clear()
            self.word_scores.clear()
            self._load_base_vocabulary()
            self._load_common_pairs()
            self._save_user_data()
        print("[PREDICTOR] Reset to default vocabulary")
    
    def export_vocabulary(self, filepath='vocabulary_export.json'):
        """Export current vocabulary to file"""
        with self.lock:
            data = {
                'frequencies': dict(self.word_frequency),
                'pairs': {w1: dict(pairs) for w1, pairs in self.word_pairs.items()},
                'user_words': list(self.user_words),
                'export_date': datetime.now().isoformat()
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"[PREDICTOR] Vocabulary exported to {filepath}")
    
    def import_vocabulary(self, filepath='vocabulary_export.json'):
        """Import vocabulary from file"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    with self.lock:
                        self.word_frequency.update(data.get('frequencies', {}))
                        for w1, pairs in data.get('pairs', {}).items():
                            for w2, count in pairs.items():
                                self.word_pairs[w1][w2] += count
                        self.user_words.update(data.get('user_words', []))
                    self._save_user_data()
                    print(f"[PREDICTOR] Vocabulary imported from {filepath}")
            except Exception as e:
                print(f"[PREDICTOR] Error importing vocabulary: {e}")
    
    def get_stats(self):
        """Get predictor statistics"""
        with self.lock:
            return {
                'total_words': len(self.word_frequency),
                'user_words': len(self.user_words),
                'word_pairs': sum(len(pairs) for pairs in self.word_pairs.values()),
                'most_common': self.word_frequency.most_common(5)
            }


# ============================================================================
# Context-Aware Predictor (Enhanced version)
# ============================================================================

class ContextAwarePredictor(KeyPredictor):
    """Enhanced predictor with context awareness and learning"""
    
    def __init__(self, user_data_file='user_dictionary.json'):
        super().__init__(user_data_file)
        self.session_history = []  # Track current session typing
        self.context_window = 3  # Remember last 3 words for context
    
    def add_to_session(self, word):
        """Add word to current session history"""
        self.session_history.append(word.lower())
        # Keep only last N words
        if len(self.session_history) > self.context_window:
            self.session_history.pop(0)
    
    def predict_with_context(self, current_word, max_suggestions=5):
        """
        Predict using full context (previous words in session)
        
        Args:
            current_word: Partial word being typed
            max_suggestions: Number of suggestions
        
        Returns:
            list: Suggestions with context awareness
        """
        if not self.session_history:
            return self.predict(current_word, None, max_suggestions)
        
        # Use last word as primary context
        previous_word = self.session_history[-1] if self.session_history else None
        
        # Get base predictions
        predictions = self.predict(current_word, previous_word, max_suggestions * 2)
        
        # Score predictions based on full context
        scored = []
        for word in predictions:
            score = self._calculate_context_score(word)
            scored.append((word, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [word for word, _ in scored[:max_suggestions]]
    
    def _calculate_context_score(self, word):
        """Calculate score based on full session context"""
        score = 0
        for i, context_word in enumerate(reversed(self.session_history)):
            weight = 1.0 / (i + 1)  # Recent words have higher weight
            if context_word in self.word_pairs:
                pair_score = self.word_pairs[context_word].get(word, 0)
                score += pair_score * weight
        return score


# ============================================================================
# Test and Demo Functions
# ============================================================================

def test_predictor():
    """Test the key predictor functionality"""
    print("=" * 60)
    print("Testing Key Predictor")
    print("=" * 60)
    
    predictor = KeyPredictor()
    
    # Test word prediction
    test_cases = [
        ("th", None),
        ("gest", None),
        ("key", None),
        ("i", "thank"),
        ("you", "thank"),
        ("click", None),
    ]
    
    for current, previous in test_cases:
        suggestions = predictor.predict(current, previous)
        print(f"\nInput: '{current}'" + (f" (after '{previous}')" if previous else ""))
        print(f"Suggestions: {suggestions}")
    
    # Test auto-correction
    misspelled = ["teh", "adn", "whta", "recieve"]
    print("\n" + "=" * 60)
    print("Auto-Correction Test:")
    for word in misspelled:
        corrected = predictor.correct_word(word)
        print(f"  '{word}' -> '{corrected}'")
    
    # Test learning
    print("\n" + "=" * 60)
    print("Learning Test:")
    predictor.learn_from_text("This is a test sentence for learning new words")
    predictor.add_word("gesturecontrol")
    
    # Test predictions after learning
    suggestions = predictor.predict("gest")
    print(f"After learning 'gesturecontrol': suggestions for 'gest' -> {suggestions}")
    
    # Test statistics
    stats = predictor.get_stats()
    print("\n" + "=" * 60)
    print("Predictor Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Predictor test completed!")


def test_context_predictor():
    """Test the context-aware predictor"""
    print("\n" + "=" * 60)
    print("Testing Context-Aware Predictor")
    print("=" * 60)
    
    predictor = ContextAwarePredictor()
    
    # Simulate typing session
    session = ["thank", "you", "for", "your"]
    print(f"\nSession context: {' '.join(session)}")
    
    for word in session:
        predictor.add_to_session(word)
    
    # Test predictions
    test_words = ["he", "ge", "wo"]
    for word in test_words:
        suggestions = predictor.predict_with_context(word)
        print(f"After context, typing '{word}': {suggestions}")


if __name__ == "__main__":
    test_predictor()
    test_context_predictor()
    
    print("\n" + "=" * 60)
    print("Key Predictor Module Ready for Integration!")
    print("=" * 60)