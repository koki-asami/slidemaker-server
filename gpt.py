from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
import time
import os
import openai

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1000,
    chunk_overlap  = 20,
    length_function = len,
)

def process_pdf(pdf_path, revision_text=None):
    loader = PyPDFLoader(pdf_path)
    pages = loader.load_and_split()

    state_of_the_union = "".join([x.page_content for x in pages])
    texts = text_splitter.create_documents([state_of_the_union])

    os.environ["OPENAI_API_KEY"]="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"

    embeddings = OpenAIEmbeddings()
    filename = "faiss_index"  # チェックするファイル名
    if os.path.isdir(filename):
        vectorstore = FAISS.load_local("faiss_index", embeddings)
    else:
        vectorstore = FAISS.from_documents(texts, embedding=embeddings)
    vectorstore.save_local("faiss_index")

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    retrieval_chain_agent = ConversationalRetrievalChain.from_llm(llm, vectorstore.as_retriever(), return_source_documents=True)

    # topic = "CAMEL"

    query = f'''
    重要なテーマを3つまでカンマ区切りで挙げてください。カンマ区切りのテーマのリストのみを出力してください。
    '''
    chat_history = []

    result = retrieval_chain_agent({"question": query, "chat_history": chat_history})
    chat_history.append(query)
    chat_history.append(result)

    results = []
    topics = result["answer"].split(",")
    print(topics)

    if len(topics) < 2:
        raise Exception
    for t in topics:
        print(t)
        query = f'{t}について要点を100字で記述してください。'
        time.sleep(10)
        result = retrieval_chain_agent({"question": query, "chat_history": []})
        results.append(result["answer"])

    status = '''
    あなたは優秀なエバンジェリストです。与えられた文章について簡潔に説明するためのスライドを作成します。
    スライドを作成する際は次のようなMarpのデザインテンプレートを使用したマークダウン形式で表現されます。
    箇条書きの文はできるだけ短くまとめてください。
    """

    ---
    <!-- スライド n -->
    # { タイトル }

    - { 本文 }
    - { 本文 }
    - { 本文 } 

    """
    '''
    prefix = [
            {"role": "system", "content": status},
    ]

    slides = []
    for r in results:
        data = f"""
    次に与えられる文章の内容についてMarpによるマークダウン形式でスライドを日本語で作成してください。
    必要に応じてスライドは2枚以上に分割してください:
    {r}

        """
        comversation = [{"role": "user", "content": data}]
        messages = prefix + comversation
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature = 0,
        )
        time.sleep(10)
        answer = response["choices"][0]["message"]["content"]
        slides.append(answer)

    output_str = """---
    marp: true
    _theme: gaia
    paginate: true
    backgroundColor: #f5f5f5

    """
    for i in slides:
        output_str += i + "\n"

    output_path = f'download/{(pdf_path.split("/")[-1]).split("/")[0]}_slide.md'
    print(output_path)
    with open(output_path, "w") as file:
        file.write(output_str)
    
    os.system(f"npx @marp-team/marp-cli@latest {output_path} --pdf -y")

    return output_path.replace(".md", ".pdf")
