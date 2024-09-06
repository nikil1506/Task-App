import google.generativeai as genai
from flask import Flask, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
import requests
import time


load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

system_instructions=(f"You are an AI trained to help with converting the given text to a computer readable format as specified. "
          "Your responses should be precise and very accurate. "
          "I will be using your response directly in my API so make sure the formatting is precise"
          "This is the general event"
          "If every other day is mentioned it means that you skip 2 days instead of one. For example, if today is monday and every other day is mentioned then the response must be Wednesday"
          "The response must be a valid json and must always contain this information after this sentence. Information is provided about the contents between !!. Anything within the  !! must not be a part of the response"
          """
             {
            "title": "<Title>", !This is the title!
            "description": "<Description", !This is the description!
            "startDate": {
              "date": "<date>", !This is the start date of the event in ISO 8601 format!
              "time": "<time>" !This is the time of the event in 24 hour format!
            },
            "repeatFrequency": "<Repeat>", !This is the repeat frequency. Repeat frequency can only have the values : days, weeks, months, years, none, custom!
            "allDay": false, !This flag should be reutrned true if the user mentions a specific time for the reminder, otherwise false!
            "repeats": {
              "interval": 1, !This is the number of times the reminder must be repeated!
              "endDate": "<date>"  !This is the end date of the event in ISO 8601 format! 
            }
          }
          
          """
        "You must strictly follow the general format which is provided above under normal circumstances where the user has provided all relevant information"
        "There are a few edge cases which will be specified below"
        "Edge case 1: The user input was $Remind me to take medicine 5 more times$ The time stamp at the event was 17.00"
        "This is a custom event"
        "In such a case a new parameter called reminders must be added which contains all the n number of timestamps needed in ISO 8601 format along with the time in 24 hour clock"
         """{
            "title": "Take medicine",
            "description": "Take it five times",
            "startDate": {
              "date": "2024-07-06 00: 00: 00.000",
              "time": "17:00"
            },
            "allDay": false,
            "repeatFrequency": "custom",
            "reminders": [
              {
                "date": "2024-07-06 00: 00: 00.000",
                "time": "18:00"
              },
              {
                "date": "2024-07-06 00: 00: 00.000",
                "time": "19:00"
              },
              {
                "date": "2024-07-06 00: 00: 00.000",
                "time": "20:00"
              },
              {
                "date": "2024-07-06 00: 00: 00.000",
                "time": "21:00"
              },
              {
                "date": "2024-07-06 00: 00: 00.000",
                "time": "22:00"
              }
            ]
          }
         """
         "Edge case 2: The user input was $Remind me to take medicine before dinner$" "This is a one time event "
         "In this case there is no repeat frequency and allday flag is always false"
         "This event also doesnt have an end date because the event ends as soon as the reminder is given"
          """{
                "title": "Take medicine",
                "description": "Take it before meal",
                "startDate": {
                  "date": "2024-07-06 00: 00: 00.000",
                  "time": "20:00"
                },
                "repeatFrequency": "none",
                "allDay": false
             }
          """
        "Edge case 3: The user input was $Remind me to take medicine every weekday until August 5$ This is a repeated event with some alterations."  
        "In this case there is a new parameter days with all the days of the week, the reminder must be sent as flags and the repeat frequency is always weeks"
        """{
                  "title": "Take medicine",
                  "description": "Take medicine every weekday until 5th aug",
                  "startDate": {
                    "date": "2024-07-06 00: 00: 00.000",
                    "time": "17:00"
                  },
                  "repeatFrequency": "weeks",
                  "allDay": false,
                  "repeats": {
                    "interval": 1,
                    "endDate": "2024-08-05 00: 00: 00.000",
                    "days": [
                      "monday",
                      "tuesday",
                      "wednesday",
                      "thursday",
                      "friday"
                    ]
                  }
                }
        """
        "Use NLP techniques to choose an appropriate time based on the information provided in the prompt when returning the time flag if the prompt does not include a time"
        "If there is no correct value for any of the mandatory fields, leave the flag for the field blank"
        "You responses MUST STRICTLY belong to one of the FOUR formats specified above under all circumstances "
        "The number of time stamps can vary depending on the text received but the format must be strictly adhered"
        "You must change the title and description based on the given text"
        # "Subtitle must describe the task but must not contain unnecessary characters"
        "Use NLP techniques to properly process the text"
        "Timestamp must be in ISO 8601 specifications. Must be accurate to the closest second. You must not add any spaces within the timestamp."
        "You must follow proper indentation"
        "Make the description as informative as possible while keeping the title simple - If the input has a verb or an action, use that as a title keeping it as small as possible"
        "Watch out for typos and other gramatical mistakes in the input. Fix them if deemed necessary. Use Advanced NLP techniques and context analysis for this purpose."
        # "Your response must not contain a ''' json <>''' ")
)



app = Flask(__name__)
CORS(app)

def simulate_conversation(prompt):
  generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
  }

  safety_settings = [
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_HATE_SPEECH",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_NONE"
    },
  ]


  model = genai.GenerativeModel(model_name="gemini-1.5-pro",
                                generation_config=generation_config,
                                safety_settings=safety_settings,
                                system_instruction=system_instructions)
  convo = model.start_chat(history=[])
  convo.send_message(prompt)
  responses=[]
  responses.append(convo.last.text)
  print(convo.last.text)
  return convo.last.text

@app.route("/process_text", methods=['POST'])
def process_text():
   data = request.json
   info=data.get('text')
   timestamp=data.get('timestamp')
   # current_date="22nd June 2024"
   time_text=f"The current date is {timestamp}"
   text=info+". "+time_text
   print("main")
   prompt = f"The following is the text you must process : {text}"
   response=simulate_conversation(prompt=prompt)
   response=response.strip("```json").strip("```")
   print(response)
   # Remove first and last line if problem arises later
   return response

if __name__ == "__main__":
    app.run(debug = True)




# def main():
  
#   predicted=simulate_conversation(prompt)
#   print(predicted)
    