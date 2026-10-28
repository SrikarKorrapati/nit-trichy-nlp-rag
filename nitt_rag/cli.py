from __future__ import annotations

import argparse

from .engine import NITTAssistant


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask questions over scraped NIT Trichy data.")
    parser.add_argument("question", help="Question to ask")
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    assistant = NITTAssistant()
    response = assistant.ask(args.question, top_k=args.top_k)

    print(f"Question type: {response.category} ({response.category_confidence:.2f})")
    print()
    print(response.answer)
    print()
    print("Extracted entities:")
    for key, values in response.entities.items():
        if values:
            print(f"- {key}: {', '.join(values[:10])}")
    print()
    print("Sources:")
    for source in response.sources[: args.top_k]:
        print(f"- [{source['score']}] {source['title']} - {source['url']}")


if __name__ == "__main__":
    main()
