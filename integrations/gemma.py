from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
from parse_llm_code import extract_first_code

## example of chatting with the model
'''chat = client.chats.create(model="gemini-2.0-flash")
response = chat.send_message("I have 2 dogs in my house.")
print(response.text)

response = chat.send_message("How many paws are in my house?")
print(response.text)

for message in chat.get_history():
    print(f'role - {message.role}',end=": ")
    print(message.parts[0].text)'''


class Google_Gemini_Integration:
    def __init__(self):
        self.client = genai.Client(api_key="AIzaSyB91l9U4eZcwqQmEYLLfyz4M8IycZ4YGbY")
        self.model = "gemma-3-12b-it"
    
    def send_message_with_system_instruction(self, system_instruction, message, max_tokens=500, temperature=0.1):
        '''response = self.client.models.generate_content(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=temperature
                ),
            contents=message
        )'''
        response = self.client.models.generate_content(
            model=self.model,
            contents=system_instruction + message
        )
        try:
            return extract_first_code(response.text).context
        except Exception as e:
            #print(f"Error extracting code: {e}")
            return response.text
      
    def generate_image(self, contents):
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                image.save('gemini-native-image.png')
                image.show()