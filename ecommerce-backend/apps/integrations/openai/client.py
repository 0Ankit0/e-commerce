from openai import OpenAI

from config import settings

from .exceptions import OpenAIClientException
from .types import OpenAICompletionResponse

client = OpenAI(api_key=settings.OPENAI_API_KEY)


OPEN_AI_API_ERROR_MSG = "OpenAI service is currently unavailable. Please try again in a couple seconds."


class OpenAIClient:
    @staticmethod
    def get_saas_ideas(keywords: list[str]) -> OpenAICompletionResponse:
        prompt = f"Get me 3-5 {', '.join(keywords)} saas ideas"

        try:
            # Note: text-davinci-003 is legacy, consider switching to gpt-3.5-turbo
            response = client.completions.create(
                model="text-davinci-003", prompt=prompt, max_tokens=200, temperature=0.5
            )
            return OpenAICompletionResponse(**response.model_dump())
        except Exception as error:
            raise OpenAIClientException(OPEN_AI_API_ERROR_MSG) from error
