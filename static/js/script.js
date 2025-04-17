// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM ready - Space Theme v2"); // Log script start

    // --- Helper function to format date for <input type="date"> ---
    function formatDateForInput(dateValue) {
        let date;
        if (!dateValue) return '';
        if (typeof dateValue === 'object' && dateValue !== null && '$date' in dateValue) {
            const timestamp = dateValue.$date;
            // Handle BSON v2 int64 represented as string in newer json_util
            const tsNumber = typeof timestamp === 'string' ? parseInt(timestamp, 10) : timestamp;
            if (typeof tsNumber === 'number') date = new Date(tsNumber);
            else return '';
        } else if (dateValue instanceof Date) { date = dateValue; }
        else { try { date = new Date(dateValue); } catch(e) { return '';} }
        if (isNaN(date.getTime())) return '';
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // --- Generic Modal Closing Logic ---
    function closeModal(modal) {
        if (modal) {
            console.log("Closing modal:", modal.id);
            modal.style.display = 'none';
        } else {
             console.error("Attempted to close a null modal");
        }
    }
    document.querySelectorAll('.modal .close-btn').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.closest('.modal')));
    });
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) closeModal(event.target);
    });


    // --- Edit Project Modal Logic ---
    const editProjectModal = document.getElementById('edit-project-modal');
    if (editProjectModal) {
        const editProjectForm = document.getElementById('edit-project-form');
        if (!editProjectForm) console.error("Edit Project Form not found!");

        function openEditProjectModal(event) {
            console.log("openEditProjectModal triggered");
            const button = event.target.closest('.edit-project-btn');
            if (!button) { console.log("Edit project button not found in event path"); return; }

            const projectId = button.dataset.projectId;
            const projectDataRaw = button.dataset.projectData;
            console.log("Project ID:", projectId);
            // console.log("Raw Project Data:", projectDataRaw); // Be careful logging potentially large data

            if(!projectId || !projectDataRaw || !editProjectForm) {
                console.error("Missing data or form for editing project.");
                alert("Cannot edit project: Internal error.");
                return;
            }

            try {
                const projectData = JSON.parse(projectDataRaw);
                console.log("Parsed Project Data:", projectData);

                editProjectForm.action = `/projects/edit/${projectId}`; // Set form action
                console.log("Set project form action to:", editProjectForm.action);

                // Populate project form
                editProjectForm.querySelector('#edit-project-name').value = projectData.name || '';
                editProjectForm.querySelector('#edit-project-desc').value = projectData.description || '';
                editProjectForm.querySelector('#edit-project-status').value = projectData.status || '';
                editProjectForm.querySelector('#edit-project-start').value = projectData.start_date ? formatDateForInput(projectData.start_date) : '';
                editProjectForm.querySelector('#edit-project-end').value = projectData.end_date ? formatDateForInput(projectData.end_date) : '';
                console.log("Populated project form fields");

                editProjectModal.style.display = 'block';
                console.log("Displayed edit project modal");
            } catch (e) {
                console.error("Error parsing project data or populating form:", e);
                console.error("Problematic data:", projectDataRaw); // Log raw data on error
                alert("Could not load project data for editing. Check console for details.");
            }
        }
        // Event delegation for project edit buttons
        const projectList = document.querySelector('.project-list');
        if (projectList) {
            projectList.addEventListener('click', (event) => {
                 if (event.target.closest('.edit-project-btn')) {
                    console.log("Edit project button clicked (delegated)");
                    openEditProjectModal(event);
                 }
            });
        } else {
            console.warn("Project list container not found for event delegation.");
        }
    } else {
         console.warn("Edit Project Modal element not found.");
    }


    // --- Edit Task Modal Logic ---
    const editTaskModal = document.getElementById('edit-task-modal');
    if (editTaskModal) {
        const editTaskForm = document.getElementById('edit-task-form');
         if (!editTaskForm) console.error("Edit Task Form not found!");

        function openEditTaskModal(event) {
             console.log("openEditTaskModal triggered");
             const button = event.target.closest('.edit-task-btn');
             if (!button) { console.log("Edit task button not found in event path"); return; }

             const taskId = button.dataset.taskId;
             const taskDataRaw = button.dataset.taskData;
             console.log("Task ID:", taskId);
             // console.log("Raw Task Data:", taskDataRaw); // Careful logging large data

             if (!taskId || !taskDataRaw || !editTaskForm) {
                 console.error("Missing data or form for editing task.");
                 alert("Cannot edit task: Internal error.");
                 return;
             }

             try {
                const taskData = JSON.parse(taskDataRaw);
                console.log("Parsed Task Data:", taskData);

                editTaskForm.action = `/tasks/edit/${taskId}`; // Set form action
                console.log("Set task form action to:", editTaskForm.action);

                // Populate task form
                editTaskForm.querySelector('#edit-task-name').value = taskData.name || '';
                editTaskForm.querySelector('#edit-task-desc').value = taskData.description || '';
                editTaskForm.querySelector('#edit-task-status').value = taskData.status || '';
                editTaskForm.querySelector('#edit-task-priority').value = taskData.priority || '';
                editTaskForm.querySelector('#edit-task-due').value = taskData.due_date ? formatDateForInput(taskData.due_date) : '';
                const estHours = taskData.estimated_hours;
                editTaskForm.querySelector('#edit-task-hours').value = (estHours !== null && estHours !== undefined) ? estHours : '';
                // Ensure hidden project ID field exists and has value (set in template)
                const projectIdField = editTaskForm.querySelector('#edit-task-project-id');
                if (!projectIdField || !projectIdField.value) {
                    console.warn("Hidden project ID field might be missing or empty in edit task modal!");
                    // Attempt to get it from the task data itself if possible
                    if(taskData.project_id && taskData.project_id.$oid) {
                         projectIdField.value = taskData.project_id.$oid;
                         console.log("Set project ID from task data fallback.");
                    }
                }
                console.log("Populated task form fields");

                editTaskModal.style.display = 'block';
                console.log("Displayed edit task modal");
             } catch (e) {
                 console.error("Error parsing task data or populating form:", e);
                 console.error("Problematic data:", taskDataRaw);
                 alert("Could not load task data for editing. Check console for details.");
             }
        }
        // Event delegation for task edit buttons
        const taskTableBody = document.querySelector('#task-table tbody');
        if(taskTableBody){
            taskTableBody.addEventListener('click', (event) => {
                 if (event.target.closest('.edit-task-btn')) {
                     console.log("Edit task button clicked (delegated)");
                     openEditTaskModal(event);
                 }
            });
        } else {
             console.warn("Task table body not found for event delegation.");
        }
    } else {
         console.warn("Edit Task Modal element not found.");
    }


    // --- Log Time Modal Logic ---
    const logTimeModal = document.getElementById('log-time-modal');
    if (logTimeModal) {
        const logTimeForm = document.getElementById('log-time-form');
        const logTimeTaskNameSpan = document.getElementById('log-time-task-name');
        if (!logTimeForm) console.error("Log Time Form not found!");
        if (!logTimeTaskNameSpan) console.error("Log Time task name span not found!");

        function openLogTimeModal(event) {
            console.log("openLogTimeModal triggered");
            const button = event.target.closest('.log-time-btn');
            if (!button) { console.log("Log time button not found in event path"); return; }

            const taskId = button.dataset.taskId;
            const taskName = button.dataset.taskName;
            console.log("Task ID:", taskId, "Task Name:", taskName);

            if (!taskId || !logTimeForm || !logTimeTaskNameSpan) {
                 console.error("Missing data or elements for logging time.");
                 alert("Cannot log time: Internal error.");
                 return;
            }

            logTimeForm.action = `/tasks/log_time/${taskId}`; // Set form action
            console.log("Set log time form action to:", logTimeForm.action);

            logTimeTaskNameSpan.textContent = taskName || 'Selected Task'; // Update modal title

            // Reset form fields
            logTimeForm.querySelector('#log-duration').value = '';
            logTimeForm.querySelector('#log-date').value = ''; // Default to empty (today)
            logTimeForm.querySelector('#log-notes').value = '';
            // Ensure hidden project ID field exists and has value (set in template)
             const projectIdField = logTimeForm.querySelector('#log-time-project-id');
                if (!projectIdField || !projectIdField.value) {
                    console.warn("Hidden project ID field might be missing or empty in log time modal!");
                    // Cannot easily get project ID here without another data attribute or query
                }
            console.log("Reset log time form fields");

            logTimeModal.style.display = 'block';
            console.log("Displayed log time modal");
        }
        // Event delegation for log time buttons
         const taskTableBody = document.querySelector('#task-table tbody'); // Reuse selector
         if(taskTableBody){
            taskTableBody.addEventListener('click', (event) => {
                 if (event.target.closest('.log-time-btn')) {
                     console.log("Log time button clicked (delegated)");
                     openLogTimeModal(event);
                 }
            });
        } else {
             console.warn("Task table body not found for event delegation (log time).");
        }
    } else {
        console.warn("Log Time Modal element not found.");
    }

}); // End DOMContentLoaded


// --- Starfield Effect (Keep as is) ---
function createStars() {
  const starfield = document.getElementById('starfield');
  if (!starfield) { return; }
  starfield.innerHTML = '';
  const starCount = 150;
  for (let i = 0; i < starCount; i++) {
    const star = document.createElement('div');
    star.classList.add('star');
    const x = Math.random() * 100; const y = Math.random() * 100;
    const size = Math.random() * 2 + 0.5; const opacity = Math.random() * 0.5 + 0.1;
    star.style.left = `${x}%`; star.style.top = `${y}%`;
    star.style.width = `${size}px`; star.style.height = `${size}px`; star.style.opacity = opacity;
    const delay = Math.random() * 5; const duration = Math.random() * 5 + 3;
    star.style.animation = `twinkle ${duration}s infinite alternate ${delay}s`;
    starfield.appendChild(star);
  }
}
createStars();