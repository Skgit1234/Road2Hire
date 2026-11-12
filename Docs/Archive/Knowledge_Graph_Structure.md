# Knowledge Graph Structure

## Objective

The Road2Hire Knowledge Graph represents skills and relationships between skills. It provides the foundation for future hybrid skill gap detection.

## Entities

The primary entity in Version 1 is:

- Skill

Each skill contains:

- Skill ID
- Skill Name

## Relationships

Version 1 supports the following relationships:

### requires

Represents a prerequisite relationship between two skills.

Example:

Machine Learning → requires → Python

### related-to

Represents a relationship between related skills.

Example:

Python → related-to → NumPy

## Graph Structure

The graph is represented using two main components:

- `skills` — contains skill nodes
- `relationships` — contains connections between skill nodes

## Version

Knowledge Graph Version: V1