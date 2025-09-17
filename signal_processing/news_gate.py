'''News Gate for filtering signals based on news sentiment and events.'''
from typing import List, Dict
from datetime import datetime, timedelta

class NewsGate:
    # Sample list of negative keywords. This should be managed in a more sophisticated way.
    NEGATIVE_KEYWORDS = [
        '압수수색', '횡령', '배임', '사기', '소송', '조사', '감사', '불공정', '과징금', '급락', '최저', '위기'
    ]

    def __init__(self, sentiment_threshold: float = -0.5, disclosure_cooldown_minutes: int = 60):
        """Initializes the NewsGate.

        Args:
            sentiment_threshold: The minimum sentiment score to pass. A signal is blocked if any recent
                                 news has a sentiment score below this value.
            disclosure_cooldown_minutes: The number of minutes to pause trading after a major disclosure.
        """
        self.sentiment_threshold = sentiment_threshold
        self.disclosure_cooldown = timedelta(minutes=disclosure_cooldown_minutes)

    def evaluate(self, symbol: str, news_data: List[Dict]) -> bool:
        """Evaluates if the news data for a symbol passes the gate.

        Args:
            symbol: The stock symbol (for logging).
            news_data: A list of news/disclosure items. Each item is a dictionary.
                         Expected keys:
                         - 'type': 'news' or 'disclosure'.
                         - 'timestamp': A datetime object for the event time.
                         - 'sentiment': A float score (-1.0 to 1.0).
                         - 'content': The string content or title of the news.

        Returns:
            True if the news conditions are met (gate is passed), False otherwise.
        """
        now = datetime.now()

        for item in news_data:
            try:
                # 1. Check for recent disclosures
                if item['type'] == 'disclosure':
                    if now - item['timestamp'] < self.disclosure_cooldown:
                        # print(f"[{symbol}] failed NewsGate: In disclosure cooldown period.")
                        return False

                # 2. Check for highly negative sentiment
                if item['sentiment'] < self.sentiment_threshold:
                    # print(f"[{symbol}] failed NewsGate: Negative sentiment detected ({item['sentiment']}).")
                    return False

                # 3. Check for negative keywords
                content = item.get('content', '').lower()
                if any(keyword in content for keyword in self.NEGATIVE_KEYWORDS):
                    # print(f"[{symbol}] failed NewsGate: Negative keyword found.")
                    return False

            except (KeyError, TypeError) as e:
                # print(f"[{symbol}] failed NewsGate: Malformed news data item. Error: {e}")
                # Decide if malformed data should fail the gate. Failing is safer.
                return False

        return True
