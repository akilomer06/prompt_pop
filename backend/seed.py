from .models import Base, engine, Session, Competition, Task, Question

IMAGE_RUBRIC = [dict(name='Composition and layout', weight=30), dict(name='Color and lighting', weight=20), dict(name='Subject and detail accuracy', weight=25), dict(name='Style and resemblance', weight=25)]
LOGO_RUBRIC = [dict(name='Relevance to the brief', weight=30), dict(name='Originality and distinctiveness', weight=25), dict(name='Visual composition', weight=20), dict(name='Readability and scalability', weight=15), dict(name='Rationale and communication', weight=10)]
QUESTIONS = [
('What does a language model use to predict the next token?', ['A fixed list of approved responses', 'Patterns learned from training data', 'A live search for every word', 'The user’s operating system'], 1),
('Which instruction is most useful for controlling output structure?', ['Make it good', 'Think harder', 'Return a JSON object with keys title and summary', 'Write something interesting'], 2),
('What is a hallucination in a language model response?', ['A confidently generated claim that is not grounded in fact', 'An image with vivid colors', 'A network timeout', 'An encrypted answer'], 0),
('Which practice best protects private information?', ['Include passwords for context', 'Remove unnecessary personal data before prompting', 'Share session cookies', 'Publish private conversation links'], 1),
('What is few-shot prompting?', ['Using a very short prompt', 'Providing examples of the desired input and output', 'Generating fewer images', 'Training a model from scratch'], 1),
('What does a model’s context window limit?', ['The number of users online', 'The total tokens it can consider in one request', 'The display resolution', 'The number of colors in an image'], 1),
('Which detail helps reproduce an image composition?', ['Only the word beautiful', 'Subject placement, camera angle, and framing', 'An unrelated brand name', 'The file creation date'], 1),
('Why should factual AI output be verified?', ['All model output is always wrong', 'Plausible language does not guarantee accuracy', 'Verification makes prompts longer', 'Models cannot write numbers'], 1),
('What is prompt injection?', ['Adding more examples', 'Untrusted content attempting to redirect model behavior', 'Compressing an image', 'Saving an output file'], 1),
('Which prompt best describes lighting?', ['Nice', 'High quality', 'Soft window light from the left with gentle shadows', 'Professional'], 2),
('What is retrieval-augmented generation intended to add?', ['Relevant external context', 'A faster monitor', 'More image pixels', 'Automatic copyright clearance'], 0),
('What is the purpose of a negative instruction in image prompting?', ['To specify unwanted visual elements', 'To reduce account security', 'To guarantee uniqueness', 'To remove all style'], 0),
('Which is a useful logo scalability check?', ['View it only at poster size', 'Verify its legibility at small sizes', 'Add tiny detail everywhere', 'Use the most possible colors'], 1),
('What should a judge do with an AI-generated score?', ['Treat it as unquestionable proof', 'Review it against the published rubric', 'Ignore the actual submission', 'Use it to automatically accuse cheating'], 1),
('What improves a prompt through iteration?', ['Changing every requirement randomly', 'Comparing output to the goal and refining specific instructions', 'Repeating only the word perfect', 'Removing all constraints'], 1),
]

def initialize():
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        if db.get(Competition, 1): return
        db.add(Competition(id=1))
        db.add(Task(id=1, round=1, title='AI knowledge quiz', duration=900, brief='Fifteen questions. One clear answer each. Your selections save automatically.', rubric=[]))
        for i in range(5):
            db.add(Task(id=i+2, round=2, title=f'Image recreation {i+1}', duration=600, grace=120, rubric=IMAGE_RUBRIC, brief='Study the reference on the presentation screen. Recreate it in your own ChatGPT session, then upload your selected image and final prompt.'))
        db.add(Task(id=7, round=3, title='The brand challenge', duration=1800, rubric=LOGO_RUBRIC, brief='', requirements=''))
        for i, (text, options, correct) in enumerate(QUESTIONS): db.add(Question(id=i+1, text=text, options=options, correct=correct, points=1))
