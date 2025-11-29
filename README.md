# IrsAttend

The Issaquah Robotics Society's Python program for managing attendance.

## Features

    •	Scan QR Codes from emailed codes
    •	Camera preview with braille
    •	Real-time attendance logging with success/failure messages
    •	Add, edit, and remove student records
    •	Manually add or remove attendance entries
    •	Import students in bulk from CSV files
    •	Email individual or all students their codes

## Run Instructions

**Prerequisites:** Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for package management.

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Activate the virtual environment:
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```powershell
     .venv\Scripts\activate
     ```
3. Run the application:
   ```bash
   python attend app -d <path-to-database-file> -c <path-to-config-file>
   ```

## Repository Structure

### Model-View-Features Architecture
I'm using a three-tier architecture that's inspired by the
[model-view-viewmodel (MVVM)](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93viewmodel)
and [model-view-presenter (MVP)](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter)
architectures. I call it *model-view-features* (MVF).
* **Model:** Contains all core database code and business logic. Model code is
   located in the src/irsattend/model subfolder.
* **View:** Contains all user interface code. If a module imports something from
   Textual, it should probably be in the view layer. View code is located in the
   src/irsattend/view subfolder.
* **Features:** Contains most everything that's not UI code, but that's not part
   of the model. The name *features* indicates that this layer supports specific
   application features that are visible in the user interface, which makes this
   layer similar to the model-view or presentation layer in other frameworks.

The MVF architecture has a few rules.
1. View-layer objects can contain references to features or model-layer objects.
2. Features can contain references to model-layer objects, but they should not
   contain references to view-layer objects.
3. Model-layer ojbects should not reference any view-layer or features objects.

#### How MVF is Different
1. Unlike the MVVM or MVP architectures, the view can retrieve data directly from the
model. During my earlier efforts to implement an MVVM architecture, I often found
that the model could provide the information needed by the view, and that sending
the information through the middle view-model layer just added complexity and
extra work.
2. Application state can be maintained within a view. For example, for a Textual
screen with a datatable, we might want to have a list of objects that corresponds
to the rows in the databable. MVVM or MVP architectures would require that the
object list be maintained in the view-model or presentation layer. MVF allows us
to maintain the object list within the view instead of creating a separate class.
I still recommend that complex data structures that contain business logic be
maintained in the features layer, to avoid mixing business logic into the view
and cluttering the view code.
3. There are no strict rules for where user-triggered events are handled. If a
user-triggered event can be handled in the view-layer with a couple lines of
code, that's probably fine. User-triggered events are not required to be sent to
the features layer. That said, the view layer should stay focused on defining the
user interface and responding to user-triggered events. Non-trival data processing
and logic should happen in the features or model layers. 

#### Final Thoughts
Perhaps you are thinking that I'm just ignorant, and that I don't really
understand how MVVM or MVP architectures are supposed to work. I concur. I've
read up on both architectures and I realized I don't have the software development
experience that's needed for a deep understanding.

I have two points to make in defense of MVF.
1. I don't develop large or highly complex applications, so I think both
MVVM an MVP are overkill for my purposes.
2. I teach Python and application development high school robotics students. I would
have trouble explaining MVVM or MVP to my students such that they could correctly
apply the architectures (note 1). But I can explain MVF.


## Notes
1. I'm aware of the Feynman rule. It probably does apply in this situation -- I
just don't care.
