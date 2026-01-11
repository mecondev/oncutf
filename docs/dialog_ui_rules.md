Dialog UI Ruleset — oncutf
0. Purpose

This document defines mandatory UI/UX rules for all dialogs in the oncutf application.

Goals:

Strict consistency across all dialogs
(same button order, same shortcuts, same default logic)

Platform-native behavior for Windows/Linux (Qt-based)

Safety-first design for batch and destructive operations

Elimination of dialog-specific ad-hoc behavior

These rules are not suggestions.
All dialogs MUST comply.

1. Target Platform

Primary platforms: Windows / Linux

UI toolkit: Qt (PyQt / PySide)

Note: macOS uses reversed button order.
oncutf is not mac-first.
Platform-specific switching may be added later if needed.

2. Button Order (Mandatory)
Core Rule

Negative action on the left, positive action on the right.

This aligns with Windows/Linux and Qt muscle memory.

Examples
Dialog Type	Button Order
Confirmation	[Cancel] [OK]
Question	[No] [Yes]
Save changes	[Discard] [Save]
Conflict	[Skip] [Overwrite]
Alternative conflict	[Skip] [Replace]

❗ Button order MUST NOT vary between dialogs.

3. Keyboard Behavior
3.1 Escape Key (Esc)

Esc MUST always cancel or close the dialog.

Esc == Cancel / Close

No exceptions

Never mapped to destructive actions

3.2 Enter Key (Default Action)

Dialogs are categorized into three classes.

4. Dialog Categories
A) Informational / Harmless Dialogs

Examples:

Info messages

Operation completed

Warnings without side effects

Buttons

[OK] or [Close]

Behavior

Default (Enter): OK / Close

Esc: Close

B) Normal Confirmation Dialogs (Non-destructive)

Examples:

“Apply settings?”

“Continue operation?”

“Proceed with import?”

Buttons

[Cancel] [OK]

[No] [Yes]

Behavior

Default (Enter): OK / Yes

Esc: Cancel / No

C) Destructive / Batch / Risky Dialogs

Examples:

Overwrite files

Delete data

Rename conflicts

Reset operations

Bulk irreversible changes

Buttons

[Cancel / Skip / No] [Do it]

Examples:

[Skip] [Overwrite]

[Cancel] [Delete]

[No] [Rename anyway]

Behavior

Default (Enter): Cancel / Skip / No

Esc: Cancel / Skip / No

Dangerous action rules

MUST NOT be default

MUST require explicit click

SHOULD use strong wording:

Overwrite

Delete

Rename anyway

❌ Avoid generic OK

This preserves platform consistency while enforcing safe defaults.

5. Labels & Wording Rules
5.1 Positive Actions

Avoid generic labels when the action is specific.

❌ Bad:

OK

✅ Good:

Rename

Overwrite

Delete

Apply

Save

Replace

5.2 Negative Actions

Use precise meaning:

Label	Meaning
Cancel	Abort entire dialog
Skip	Continue but ignore current item
No	Negative answer to a question
Discard	Drop changes
5.3 Non-Destructive Alternatives

When available, prefer explicit alternatives:

Keep both

Rename automatically

Skip

Skip all

6. Safety Patterns (Conditional)
6.1 “Don’t ask again”

Allowed ONLY if:

Dialog appears frequently

Action is reversible OR safe default exists

Must NOT be used for irreversible destructive actions.

6.2 “Apply to all”

For conflict loops (rename, overwrite):

Provide either:

Skip / Skip all

Overwrite / Overwrite all

OR

A checkbox:

☐ Apply this choice to remaining conflicts

6.3 Very Dangerous Operations

Examples:

Permanent delete

Data wipe

Cache purge without recovery

Rules:

No default button
OR

Explicit confirmation checkbox:

☐ I understand this action is irreversible

7. Focus vs Default (Critical Distinction)

Default → action triggered by Enter

Focus → initially highlighted widget

Rules

Normal dialogs:

Focus may be on primary input field

Default may be Accept

Destructive dialogs:

Focus MUST be on safe button

Default MUST be safe action

8. Qt Implementation Rules (Mandatory)
8.1 Button Creation

All dialogs MUST use QDialogButtonBox.

❌ Forbidden:

Ad-hoc QPushButton layouts

Manual key handling per dialog

8.2 Button Roles

Buttons MUST be assigned roles:

Action	Role
OK / Yes / Apply / Rename	AcceptRole
Cancel / No / Close / Skip	RejectRole
Delete / Overwrite / Reset	DestructiveRole
8.3 Default Button Handling

For destructive dialogs:

Safe button:

safe_button.setDefault(True)
safe_button.setAutoDefault(True)


Dangerous button:

dangerous_button.setDefault(False)
dangerous_button.setAutoDefault(False)

8.4 Signals

Dialogs MUST connect:

button_box.accepted.connect(self.accept)
button_box.rejected.connect(self.reject)


Manual keyPressEvent overrides are forbidden unless strictly necessary.

9. oncutf Default Policy Summary

Platform: Windows / Linux

Button order: Negative → Positive

Esc: Always cancels

Enter:

Normal dialogs → Accept

Risky dialogs → Cancel / Skip

Labels: Action-specific, never generic

10. Enforcement

Any new dialog MUST follow this document.

Any refactored dialog MUST be updated to comply.

Violations should be treated as UI bugs, not stylistic differences.

Button width policy (oncutf)

Default

All buttons in the same dialog MUST have equal width.

Exceptions

Single-button dialogs

Non-destructive dialogs with a clearly defined primary action

Forbidden

Dynamic width in destructive or batch dialogs

CTA dominance through size for dangerous actions

code example:
buttons = button_box.buttons()
max_width = max(btn.sizeHint().width() for btn in buttons)

for btn in buttons:
    btn.setMinimumWidth(max_width)

End of document