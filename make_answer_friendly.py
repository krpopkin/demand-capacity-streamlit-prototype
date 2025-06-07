from typing import List, Tuple
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

def format_result(
    question: str,
    result: List[Tuple],
    llm
) -> str:
    """
    Turn a raw result into a human-friendly response.

    Args:
      question: the original user question (e.g. "Which team members are assigned to Product X?")
      result:  list of 1-tuples from db.run(raw_sql) (e.g. [('San Mishra',), ('Ken Popkin',)])
      llm:      a ChatVertexAI (or any LangChain LLM) instance

    Returns:
      A natural language answer.
    """
    # flatten list of 1-tuples
    rows = [row[0] for row in result]

    # build the prompt
    formatter = PromptTemplate(
        input_variables=["question", "rows"],
        template="""
                    You are a helpful assistant that transforms raw results into a human-friendly answer that is no more 
                    than two sentences.

                    User question:
                    {question}

                    Raw SQL result:
                    {rows}
                    """)

    # run it through the LLM
    chain = LLMChain(llm=llm, prompt=formatter)
    return chain.run(question=question, rows=rows)
