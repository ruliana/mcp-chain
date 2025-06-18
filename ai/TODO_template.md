# {PROJECT_NAME} TODO - AI Memory System

<!-- AI ASSISTANT INSTRUCTIONS:
This TODO.md serves as your persistent memory for long-term tasks. You should:
1. WIPE this file when user requests new multi-phase task and recreate from template
2. UPDATE this file continuously while working - add progress, problems, solutions
3. CREATE local detailed plans at start of each phase before implementation
4. RECORD any problems that trip you up to avoid repeating them
5. USE this file to resume work in new sessions - all context should be here
-->

**Task Description:** {TASK_DESCRIPTION}

**Current Status:** {CURRENT_STATUS} | **Active Phase:** {CURRENT_PHASE}

## 🎯 **Task Objective**
{MAIN_GOAL_DESCRIPTION}

## 📋 **Useful Commands & Context**

<!-- AI: Update this section with project-specific commands and important context -->
{PROJECT_SPECIFIC_COMMANDS}

## 🧠 **AI Memory Notes**

### Problems Encountered & Solutions
<!-- AI: Record significant issues here to avoid repeating them -->
- **Problem:** {PROBLEM_DESCRIPTION}
  - **Solution:** {SOLUTION_USED}
  - **Lesson:** {WHAT_TO_REMEMBER}

### Successful Patterns
<!-- AI: Document what works well for this project -->
- **Pattern:** {SUCCESSFUL_APPROACH}
  - **When to use:** {CONTEXT_FOR_REUSE}

### Context for Next Session
<!-- AI: Update before ending session - what does the next AI need to know? -->
- **Current state:** {WHERE_WE_ARE}
- **Next steps:** {WHAT_TO_DO_NEXT}
- **Important context:** {KEY_INFORMATION_TO_REMEMBER}

## 📋 **Implementation Phases**

### Phase 1: {PHASE_1_NAME}
**Objective:** {PHASE_1_OBJECTIVE}

<!-- AI: Create local plan here before starting implementation -->
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] {DETAILED_SUBTASK_1}
- [ ] {DETAILED_SUBTASK_2}
- [ ] {DETAILED_SUBTASK_3}

**Status:** {NOT_STARTED|IN_PROGRESS|COMPLETED}
**Results:** {OUTCOMES_AND_ACHIEVEMENTS}

### Phase 2: {PHASE_2_NAME}
**Objective:** {Phase_2_OBJECTIVE}

**Dependencies:** Requires Phase 1 completion
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] {DETAILED_SUBTASK_1}
- [ ] {DETAILED_SUBTASK_2}

**Status:** {NOT_STARTED|IN_PROGRESS|COMPLETED}
**Results:** {OUTCOMES_AND_ACHIEVEMENTS}

### Phase 3: {PHASE_3_NAME}
**Objective:** {PHASE_3_OBJECTIVE}

**Dependencies:** Requires Phase 2 completion
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] {DETAILED_SUBTASK_1}
- [ ] {DETAILED_SUBTASK_2}

**Status:** {NOT_STARTED|IN_PROGRESS|COMPLETED}
**Results:** {OUTCOMES_AND_ACHIEVEMENTS}

<!-- AI: Add more phases as needed for your specific task -->

## 🧪 **Testing Strategy**
<!-- AI: Update with task-specific testing approach -->
{TESTING_APPROACH_DESCRIPTION}

1. **Validation Approach:** {HOW_TO_VALIDATE_EACH_PHASE}
2. **Integration Testing:** {HOW_TO_TEST_COMPLETE_SYSTEM}
3. **Success Verification:** {HOW_TO_KNOW_TASK_IS_COMPLETE}

## 📝 **Success Criteria**
<!-- AI: Define clear completion criteria -->
- [ ] {SUCCESS_CRITERION_1}
- [ ] {SUCCESS_CRITERION_2}
- [ ] {SUCCESS_CRITERION_3}
- [ ] {SUCCESS_CRITERION_4}

## 🎉 **Completed Milestones**
<!-- AI: Record major achievements here -->

### ✅ **{MILESTONE_NAME}**
- **Achievement:** {WHAT_WAS_ACCOMPLISHED}
- **Impact:** {WHY_THIS_MATTERS}
- **Date:** {COMPLETION_DATE}

## 🚨 **Risk Mitigation**
<!-- AI: Update with risks discovered during implementation -->
- **Risk:** {POTENTIAL_PROBLEM}
  - **Mitigation:** {HOW_TO_PREVENT_OR_HANDLE}
- **Risk:** {ANOTHER_POTENTIAL_PROBLEM}
  - **Mitigation:** {PREVENTION_STRATEGY}

---

## 📖 **Template Usage Example**

<!-- This section shows AI assistants how to properly use this template -->

### Example: Adding New Feature to Python Project

```markdown
# Python Project Feature Addition TODO - AI Memory System

**Task Description:** Add user authentication system to existing Flask web application

**Current Status:** Phase 1 Implementation | **Active Phase:** Phase 1

## 🎯 **Task Objective**
Implement secure user authentication with registration, login, logout, and session management using Flask-Login and bcrypt for password hashing.

## 📋 **Useful Commands & Context**

This project uses Flask with SQLAlchemy ORM:
- `flask run` - Start development server
- `flask db migrate` - Create database migration
- `flask db upgrade` - Apply database migrations
- `pytest tests/` - Run test suite
- Dependencies: Flask-Login, bcrypt, SQLAlchemy

## 🧠 **AI Memory Notes**

### Problems Encountered & Solutions
- **Problem:** Flask-Login import failing with circular import error
  - **Solution:** Moved user_loader callback to after app initialization in __init__.py
  - **Lesson:** Be careful with Flask app factory pattern and extension initialization order

### Successful Patterns
- **Pattern:** Using TDD with pytest fixtures for authentication testing
  - **When to use:** Any time testing Flask routes that require authentication

### Context for Next Session
- **Current state:** Phase 1 database models completed, working on Flask-Login integration
- **Next steps:** Complete user authentication routes and add password hashing
- **Important context:** Database schema is finalized, don't modify User table structure

## 📋 **Implementation Phases**

### Phase 1: Core Authentication Infrastructure
**Objective:** Set up database models, Flask-Login integration, and basic auth routes

**Local Plan:**
- [x] Create User model with SQLAlchemy
- [x] Add Flask-Login dependency and configuration
- [ ] Implement user registration route with validation
- [ ] Add password hashing with bcrypt
- [ ] Create login/logout routes
- [ ] Add session management

**Status:** IN_PROGRESS
**Results:** User model created, Flask-Login configured successfully

### Phase 2: Frontend Integration
**Objective:** Create HTML templates and forms for authentication

**Dependencies:** Requires Phase 1 completion
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] Design registration form template
- [ ] Create login form template
- [ ] Add navigation links for auth status
- [ ] Style forms with CSS framework

**Status:** NOT_STARTED

### Phase 3: Security Hardening & Testing
**Objective:** Add comprehensive security measures and test coverage

**Dependencies:** Requires Phase 2 completion
**Local Plan:** (Create detailed sub-tasks when starting this phase)
- [ ] Add CSRF protection
- [ ] Implement rate limiting for login attempts
- [ ] Add comprehensive test suite
- [ ] Security audit and penetration testing

**Status:** NOT_STARTED
```

### Key Template Customization Points:

1. **Replace ALL {VARIABLE_NAME} placeholders** with actual project content
2. **Customize phases** to match your specific task requirements  
3. **Update commands section** with project-specific development commands
4. **Set realistic objectives** for each phase
5. **Create detailed local plans** before starting each phase implementation

### AI Assistant Reminders:

- **Update frequently**: Mark tasks complete, record problems, update context
- **Plan before implementing**: Always create local plans with specific sub-tasks
- **Document everything**: Problems, solutions, successful patterns, context changes
- **Prepare for handoff**: Each session should end with clear next steps

---

<!-- AI REMINDER: This TODO should be a living document. Update it frequently with:
- Progress on current phase
- New problems discovered and how you solved them
- Changes to approach or strategy
- Context needed for next session
- Any insights or learnings that would help future work
-->

**Last Updated:** {LAST_UPDATE_DATE} | **Next AI Session:** Should start with Phase {NEXT_PHASE} 