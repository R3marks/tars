# Tars Design Doc

This document serves to outline an initial set of features for the app, and how requirements for a given use case will be fulfilled.

## Features

### Natural conversation

I want this AI assistant to feel like a human being, such that conversation is natural and fluid, as if talking to a senior engineer or professor.

Natural conversation aids me by:
 - Removing communication bottlenecks
 - Acting on behalf to retrieve whatever information is needed, including asking for more input from myself where necessary
 - Challenging my work and design decisions to consider alternative approaches to development


### Multimodal input

Ideally a fully local AI assistant should be able to act as if in the same room as me, looking at my screen.

Multimodal input aids me by:
 - Providing the assistant with as much context as possible
 - Allowing the assistant to see the output of their suggestions
 - Removing communication bottlenecks

### Memory

I want to be able to assume that the assistant remembers everything we've discussed, so I don't need to keep providing the same context.

Memory aids me by:
 - Not having to send the same context over and over again
 - Tailoring responses to my style 
 - Matching my personality in a way a friend would learn about me

### Actionable Agency

I want my assistant to not just be a passive bystander, but one that can perform actions on my behalf.

Actionable Agency aids me by:
 - Making code changes on my behalf (file editing, saving, deleting, suggesting etc.)
 - Reading documentation on my behalf to search for answers
 - Removing communication bottlenecks

 ## Initial use case

 The first use case I have in mind, which can serve as a test for how well my assistant can perform, is that I'd like to create a mobile app, through the entire Software Development Life Cycle (SDLC), and I'd like my assistant to aid me in the development of this app. 

 ### Essential requirements
  - **Knowledge**: Know how to create an android app
  - **Coding**: Code/help me code
  - **Vision**: See how the app looks like

## MVP Solution

To achieve the requirements listed out above, I'll scope out a 3 tiered solution for each requirement.

### Knowledge
MVP:
 - Should be able to consume the most recent documentation for creating an android app

Improvements:
 - Can search for information itself that goes beyond the documentation

### Coding
MVP:
 - Competent enough model to be able to code correctly or understand why code isn't working

Improvements:
 - Ability to make code suggestions within the IDE

### Vision
MVP:
 - See a screenshot of my app so that it understands the output of it's suggestions

Improvements:
 - Use my app by direct control to evaluate how well it performs, and to test functionality

By focusing on an MVP solution, scope can remain limited, and naturally grow throughout development

## Alignment of desired features and requirements

The above use case will allow for the development of an assistant that will achieve the following; checked boxes indicate progress towards an MVP solution, whilst unchecked boxes are areas for potential improvements:

### Natural conversation
 - [x] Consume additional context beyond a single prompt
 - [ ] Asynchronously retrieving information from the web/documentation
 - [ ] Routing queries to a code llm

### Multimodal input
 - [x] Process image prompts

### Memory
 - [x] Store documentation as knowledge base 
 - [ ] Recall all relevant context for continued development fo the app

### Actionable Agency
 - [ ] Use/test the application like a user
 - [ ] Suggest code inside an IDE or ability to edit files