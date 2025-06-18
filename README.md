# LLM_Analysis
This repository is where the code for my project in statistics 02445 will be uploaded.

# Prerequisits
Python version above 3.9.\\
To run the Azure Openai it is needed to run az login as seen in the Microsoft AI foundry documentation. This is though personalized and is recommended to replace the API-endpoint in the connection.py file with your own endpoint. \\
Then run the pip command "install -r requirements.txt" which will install all the required files needed.

# Coding credit:
## Microsoft Azure AIfoudry https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview?pivots=programming-language-python
Without a staple API in which the prompts could quickly be processed this report would not have been able to be made
## Crossref.org https://www.crossref.org/documentation/retrieve-metadata/rest-api/
For their rest-api documentation without it none of this would be possible in accodance with their CC0 licence.
## Openalex https://docs.openalex.org/
For their large collection of entities which could sub in when the crossref failed
## Google Books https://developers.google.com/books
For their collection of books which was a failsafe when both OpenAlex and Crossref failed. 
So portions of the output is validated on work created and shared by Google and used according to terms described in the Creative Commons 4.0 Attribution License.
## Rapidfuzz and all its contributors https://github.com/rapidfuzz/RapidFuzz
For their fuzz functions making it possible to validate each author and title and give a fuzz score. 
Used in accordance to the MIT-license
## Pandas https://pandas.pydata.org/docs/user_guide/index.html
For a brilliant user guide which made it easy to use .csv as a dataframe. Used in accordance with the BSD 3-Clause License.
BSD 3-ClauseLicence.txt

# Licensing:
My work is to be freely used in accordance to the MIT license listed in the licence file. This is though only my code, and therefore any of the coding credits license weigh higher than mine. So if trying to replicate the test, pls read the credits licence policy.


# Contact
You can contact me on my 02445@horizon0.anonaddy.com mail i wont always be able to answer but would gladly try to help.