class App {
    constructor() {
        this.currentProject = null;
        this.projects = [];
    }

    async init() {
        this.setupNavigation();
        this.setupTabs();
        await this.loadSettings();
        await this.loadTemplates();
        await this.scanProjects();
    }

    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                const btn = e.currentTarget;
                btn.classList.add('active');
                this.switchView(btn.dataset.view);
            });
        });
    }

    setupTabs() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const target = e.currentTarget.dataset.target;
                
                // Update active tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                e.currentTarget.classList.add('active');
                
                // Update active content
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(target).classList.add('active');
            });
        });
    }

    switchView(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`${viewId}-view`).classList.add('active');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message; // Auto-escaped
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // JS Bridge Calls
    async callBridge(method, payload = null) {
        try {
            if (payload !== null) {
                return await window.pywebview.api[method](payload);
            } else {
                return await window.pywebview.api[method]();
            }
        } catch (err) {
            this.showToast(err.toString(), 'error');
            throw err;
        }
    }

    async loadSettings() {
        try {
            const settings = await this.callBridge('get_settings');
            document.getElementById('setting-theme').value = settings.theme;
            document.getElementById('setting-root').value = (settings.workspace_roots || []).join('\n');
            document.getElementById('setting-ai-provider').value = settings.ai_provider;
            document.getElementById('setting-ai-base-url').value = settings.ai_base_url || '';
            document.getElementById('setting-ai-model').value = settings.ai_model || 'gpt-4o-mini';
            document.getElementById('setting-ai-streaming').checked = Boolean(settings.ai_streaming);
            // Never expose ai_api_key back to DOM. We just show if it's configured.
            document.getElementById('setting-ai-key').placeholder = settings.ai_key_configured ? '******** (configured)' : 'Enter API key...';
            document.getElementById('setting-ai-key').value = '';
            
            // Apply theme
            if (settings.theme === 'dark') document.body.classList.add('dark');
            else document.body.classList.remove('dark');
        } catch (e) {
            console.error("Failed to load settings:", e);
        }
    }

    async loadTemplates() {
        try {
            const templates = await this.callBridge('get_templates');
            const select = document.getElementById('np-template');
            // Keep the first default option
            select.innerHTML = '<option value="">-- No Template (Blank) --</option>';
            templates.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.id;
                opt.textContent = `${t.name} (v${t.version})`;
                select.appendChild(opt);
            });
        } catch (e) {
            console.error("Failed to load templates:", e);
        }
    }

    async saveSettings() {
        const payload = {
            theme: document.getElementById('setting-theme').value,
            workspace_roots: document.getElementById('setting-root').value
                .split(/\r?\n/)
                .map(path => path.trim())
                .filter(Boolean),
            ai_provider: document.getElementById('setting-ai-provider').value,
            ai_base_url: document.getElementById('setting-ai-base-url').value,
            ai_model: document.getElementById('setting-ai-model').value,
            ai_streaming: document.getElementById('setting-ai-streaming').checked,
            ai_api_key: document.getElementById('setting-ai-key').value // Only sent if not empty
        };
        await this.callBridge('update_settings', payload);
        this.showToast('Settings saved successfully', 'success');
        this.loadSettings();
    }

    async scanProjects() {
        this.showToast('Scanning workspaces...');
        try {
            const res = await this.callBridge('scan_projects');
            this.projects = res.projects;
            this.renderProjectsGrid();
            this.loadDashboardMetrics();
            if (res.warnings && res.warnings.length) {
                this.showToast('Scan completed with warnings', 'warning');
            } else {
                this.showToast('Scan completed', 'success');
            }
        } catch (e) {}
    }

    async loadDashboardMetrics() {
        try {
            const metrics = await this.callBridge('get_dashboard_metrics');
            const container = document.getElementById('dashboard-metrics');
            container.textContent = `Projects: ${metrics.projects} · Tasks: ${metrics.tasks_done}/${metrics.tasks_total} done · Attached artifacts: ${metrics.artifacts_attached}`;
        } catch (e) {
            console.error('Failed to load dashboard metrics:', e);
        }
    }

    async searchProjects() {
        const query = document.getElementById('project-search').value.trim();
        if (!query) {
            await this.scanProjects();
            return;
        }
        const results = await this.callBridge('search_projects', query);
        this.projects = results.map(project => ({
            id: project.id,
            metadata: {
                project_name: project.project_name,
                customer_name: project.customer_name,
                project_type: project.project_type,
                stage: project.stage,
                updated_at: new Date().toISOString()
            }
        }));
        this.renderProjectsGrid();
    }

    renderProjectsGrid() {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = '';
        
        if (this.projects.length === 0) {
            const msg = document.createElement('div');
            msg.style = 'grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;';
            msg.textContent = 'No workspaces found. Create one or sync your directory.';
            grid.appendChild(msg);
            return;
        }

        this.projects.forEach(p => {
            const card = document.createElement('div');
            card.className = 'project-card';
            card.onclick = () => this.openProject(p);
            
            const date = new Date(p.metadata.updated_at).toLocaleDateString();
            
            const header = document.createElement('div');
            header.className = 'card-header';
            const badge = document.createElement('div');
            badge.className = 'badge';
            badge.textContent = p.metadata.project_type;
            header.appendChild(badge);
            
            const body = document.createElement('div');
            const h3 = document.createElement('h3');
            h3.textContent = p.metadata.project_name;
            const customer = document.createElement('div');
            customer.className = 'customer';
            customer.textContent = p.metadata.customer_name;
            body.appendChild(h3);
            body.appendChild(customer);
            
            const footer = document.createElement('div');
            footer.className = 'card-footer';
            const spanStage = document.createElement('span');
            spanStage.textContent = p.metadata.stage;
            const spanDate = document.createElement('span');
            spanDate.textContent = `Updated: ${date}`;
            footer.appendChild(spanStage);
            footer.appendChild(spanDate);
            
            card.appendChild(header);
            card.appendChild(body);
            card.appendChild(footer);
            
            grid.appendChild(card);
        });
    }

    openNewProjectModal() {
        document.getElementById('modal-new-project').classList.remove('hidden');
    }

    closeModal(id) {
        document.getElementById(id).classList.add('hidden');
    }

    async submitNewProject() {
        const payload = {
            name: document.getElementById('np-name').value,
            customer: document.getElementById('np-customer').value,
            project_type: document.getElementById('np-type').value,
            template_id: document.getElementById('np-template').value
        };
        await this.callBridge('create_project', payload);
        this.closeModal('modal-new-project');
        this.showToast('Project created', 'success');
        this.scanProjects();
    }

    openProject(project) {
        this.currentProject = project;
        document.getElementById('pd-name').textContent = project.metadata.project_name;
        document.getElementById('pd-customer').textContent = project.metadata.customer_name;
        
        this.switchView('project-details');
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        
        this.loadProjectDetails();
        this.loadAuditLog();
    }

    async attachArtifact(artifactId) {
        try {
            const path = await this.callBridge('open_file_dialog');
            if (!path) return; // User cancelled
            
            this.showToast('Attaching file...', 'info');
            await this.callBridge('attach_artifact', { 
                project_id: this.currentProject.id, 
                artifact_id: artifactId,
                file_path: path 
            });
            this.showToast('File attached successfully', 'success');
            this.loadProjectDetails();
            this.loadAuditLog();
        } catch (e) {
            console.error(e);
            // Toast is handled by callBridge on error
        }
    }

    async createPackage() {
        const res = await this.callBridge('create_package', { project_id: this.currentProject.id });
        this.showToast(`Package created: ${res.path}`, 'success');
        this.loadAuditLog();
    }

    async undoImport() {
        await this.callBridge('undo_import', { project_id: this.currentProject.id });
        this.showToast('Last import undone', 'success');
        await this.loadProjectDetails();
        await this.loadAuditLog();
    }

    async createTask() {
        const title = window.prompt('Task title:');
        if (!title || !title.trim()) return;
        await this.callBridge('create_task', { project_id: this.currentProject.id, title: title.trim() });
        this.showToast('Task created', 'success');
        await this.loadProjectDetails();
    }

    async editProjectMetadata() {
        const details = await this.callBridge('get_project_details', this.currentProject.id);
        const metadata = details.metadata;
        const projectName = window.prompt('Project name:', metadata.project_name);
        if (!projectName || !projectName.trim()) return;
        const customerName = window.prompt('Customer name:', metadata.customer_name);
        if (!customerName || !customerName.trim()) return;
        const stage = window.prompt('Stage: planning, active, blocked, closed, archived', metadata.stage);
        if (!stage || !stage.trim()) return;
        await this.callBridge('update_project_metadata', {
            project_id: this.currentProject.id,
            project_name: projectName.trim(),
            customer_name: customerName.trim(),
            stage: stage.trim().toLowerCase()
        });
        this.currentProject.metadata.project_name = projectName.trim();
        this.currentProject.metadata.customer_name = customerName.trim();
        this.currentProject.metadata.stage = stage.trim().toLowerCase();
        document.getElementById('pd-name').textContent = projectName.trim();
        document.getElementById('pd-customer').textContent = customerName.trim();
        this.showToast('Project details updated', 'success');
    }

    async createArtifact() {
        const type = window.prompt('Artifact name/type:');
        if (!type || !type.trim()) return;
        await this.callBridge('create_artifact', { project_id: this.currentProject.id, type: type.trim() });
        this.showToast('Artifact created', 'success');
        await this.loadProjectDetails();
    }

    async createSite() {
        const name = window.prompt('Site name:');
        if (!name || !name.trim()) return;
        await this.callBridge('create_site', { project_id: this.currentProject.id, name: name.trim() });
        this.showToast('Site created', 'success');
        await this.loadProjectDetails();
    }

    async createDevice() {
        const details = await this.callBridge('get_project_details', this.currentProject.id);
        if (!details.sites.length) {
            this.showToast('Create a site before adding a device.', 'warning');
            return;
        }
        const siteName = details.sites.map(site => `${site.name} (${site.site_id})`).join('\n');
        const siteId = window.prompt(`Site ID:\n${siteName}`);
        if (!siteId) return;
        const serialNumber = window.prompt('Device serial number:');
        if (!serialNumber || !serialNumber.trim()) return;
        const managementIp = window.prompt('Management IP (optional):') || '';
        await this.callBridge('create_device', {
            project_id: this.currentProject.id,
            site_id: siteId.trim(),
            serial_number: serialNumber.trim(),
            management_ip: managementIp.trim()
        });
        this.showToast('Device created', 'success');
        await this.loadProjectDetails();
    }

    async importDevicesCsv() {
        const sourcePath = await this.callBridge('open_file_dialog');
        if (!sourcePath) return;
        const operation = await this.callBridge('import_devices_csv', {
            project_id: this.currentProject.id,
            source_path: sourcePath
        });
        this.showToast('CSV import started', 'info');
        const poll = async () => {
            const status = await this.callBridge('get_operation', operation.operation_id);
            if (status.status === 'running') {
                setTimeout(poll, 500);
            } else if (status.status === 'success') {
                this.showToast(`Imported ${status.path} device(s)`, 'success');
                await this.loadProjectDetails();
            } else {
                this.showToast('CSV import failed; no inventory changes were saved.', 'error');
            }
        };
        poll();
    }

    async createBackup() {
        const operation = await this.callBridge('create_backup', { project_id: this.currentProject.id });
        this.showToast('Backup started', 'info');
        const poll = async () => {
            const status = await this.callBridge('get_operation', operation.operation_id);
            if (status.status === 'running') {
                setTimeout(poll, 500);
            } else if (status.status === 'success') {
                this.showToast(`Backup created: ${status.path}`, 'success');
            } else {
                this.showToast('Backup failed. Review application logs for details.', 'error');
            }
        };
        poll();
    }

    async restoreBackup() {
        const backups = await this.callBridge('list_backups', this.currentProject.id);
        if (!backups.length) {
            this.showToast('No backups are available for this project.', 'warning');
            return;
        }
        const backupPath = window.prompt(`Backup path to restore:\n${backups.join('\n')}`, backups[0]);
        if (!backupPath) return;
        const operation = await this.callBridge('restore_backup', {
            project_id: this.currentProject.id,
            backup_path: backupPath.trim()
        });
        this.showToast('Restore started in a new project directory.', 'info');
        const poll = async () => {
            const status = await this.callBridge('get_operation', operation.operation_id);
            if (status.status === 'running') {
                setTimeout(poll, 500);
            } else if (status.status === 'success') {
                this.showToast(`Restored to: ${status.path}`, 'success');
                await this.scanProjects();
            } else {
                this.showToast('Restore failed. The incomplete restore was retained for recovery.', 'error');
            }
        };
        poll();
    }

    async deleteTask(taskId, title) {
        if (!window.confirm(`Remove task "${title}"? This does not delete files.`)) return;
        await this.callBridge('delete_task', { project_id: this.currentProject.id, task_id: taskId });
        this.showToast('Task removed', 'success');
        await this.loadProjectDetails();
    }

    async deleteArtifact(artifactId, type) {
        if (!window.confirm(`Remove artifact "${type}"? Its attached file will remain on disk.`)) return;
        await this.callBridge('delete_artifact', { project_id: this.currentProject.id, artifact_id: artifactId });
        this.showToast('Artifact removed', 'success');
        await this.loadProjectDetails();
    }

    async updateArtifactStatus(artifactId, status) {
        await this.callBridge('update_artifact', {
            project_id: this.currentProject.id,
            artifact_id: artifactId,
            status
        });
        this.showToast('Artifact approval updated', 'success');
        await this.loadProjectDetails();
    }

    async loadProjectDetails() {
        const [data, projectDetails] = await Promise.all([
            this.callBridge('get_checklist', this.currentProject.id),
            this.callBridge('get_project_details', this.currentProject.id)
        ]);
        
        // 1. Render Workflow (Tasks)
        const wfContainer = document.getElementById('workflow-phases');
        wfContainer.innerHTML = '';
        
        if (data.tasks.length === 0) {
            wfContainer.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px;">No tasks found. Use a Template to initialize tasks.</div>';
        } else {
            // Group tasks by phase
            const phases = {};
            data.tasks.forEach(t => {
                const p = t.phase || 'Uncategorized';
                if (!phases[p]) phases[p] = [];
                phases[p].push(t);
            });
            
            for (const [phase, tasks] of Object.entries(phases)) {
                const group = document.createElement('div');
                group.className = 'phase-group';
                
                const header = document.createElement('div');
                header.className = 'phase-header';
                header.textContent = phase;
                group.appendChild(header);
                
                tasks.forEach(t => {
                    const card = document.createElement('div');
                    card.className = 'task-card';
                    
                    const info = document.createElement('div');
                    info.className = 'task-info';
                    const title = document.createElement('h4');
                    title.textContent = t.title;
                    const description = document.createElement('p');
                    description.textContent = t.description || '';
                    info.appendChild(title);
                    info.appendChild(description);
                    
                    const meta = document.createElement('div');
                    meta.className = 'task-meta';
                    
                    const priority = document.createElement('span');
                    priority.style.fontSize = '0.75rem';
                    priority.style.color = 'var(--text-muted)';
                    priority.textContent = `Priority: ${t.priority}`;
                    
                    const select = document.createElement('select');
                    select.className = 'status-select';
                    select.innerHTML = `
                        <option value="To Do" ${t.status === 'To Do' ? 'selected' : ''}>To Do</option>
                        <option value="In Progress" ${t.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                        <option value="Blocked" ${t.status === 'Blocked' ? 'selected' : ''}>Blocked</option>
                        <option value="Done" ${t.status === 'Done' ? 'selected' : ''}>Done</option>
                    `;
                    select.onchange = async (e) => {
                        await this.callBridge('update_checklist', { 
                            project_id: this.currentProject.id, 
                            task_id: t.id,
                            status: e.target.value
                        });
                        // Visual update
                        if (e.target.value === 'Done') select.className = 'status-select status-done';
                        else if (e.target.value === 'In Progress') select.className = 'status-select status-progress';
                        else select.className = 'status-select status-todo';
                    };
                    
                    // Initial color
                    if (t.status === 'Done') select.className = 'status-select status-done';
                    else if (t.status === 'In Progress') select.className = 'status-select status-progress';
                    else select.className = 'status-select status-todo';
                    
                    meta.appendChild(priority);
                    meta.appendChild(select);

                    const remove = document.createElement('button');
                    remove.className = 'btn btn-secondary';
                    remove.style = 'font-size:0.75rem; padding:5px 8px;';
                    remove.textContent = 'Remove';
                    remove.onclick = () => this.deleteTask(t.id, t.title);
                    meta.appendChild(remove);
                    
                    card.appendChild(info);
                    card.appendChild(meta);
                    group.appendChild(card);
                });
                
                wfContainer.appendChild(group);
            }
        }

        const rolloutContainer = document.getElementById('rollout-matrix');
        rolloutContainer.innerHTML = '';
        if (projectDetails.sites.length === 0) {
            rolloutContainer.textContent = 'No rollout sites configured.';
        } else {
            projectDetails.sites.forEach(site => {
                const group = document.createElement('div');
                group.className = 'phase-group';
                const title = document.createElement('div');
                title.className = 'phase-header';
                title.textContent = site.name;
                group.appendChild(title);
                const devices = projectDetails.devices.filter(device => device.site_id === site.site_id);
                if (!devices.length) {
                    const empty = document.createElement('p');
                    empty.textContent = 'No devices assigned.';
                    group.appendChild(empty);
                }
                devices.forEach(device => {
                    const deviceRow = document.createElement('div');
                    deviceRow.className = 'task-card';
                    deviceRow.textContent = `${device.serial_number} · ${device.management_ip || 'No IP'} · Pre: ${device.pre_check_status} · Post: ${device.post_check_status} · UAT: ${device.uat_status}`;
                    group.appendChild(deviceRow);
                });
                rolloutContainer.appendChild(group);
            });
        }
        
        // 2. Render Artifacts
        const artContainer = document.getElementById('artifacts-grid');
        artContainer.innerHTML = '';
        
        if (data.artifacts.length === 0) {
            artContainer.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px;grid-column:1/-1;">No artifacts required.</div>';
        } else {
            data.artifacts.forEach(a => {
                const card = document.createElement('div');
                card.className = `artifact-card ${a.path ? 'has-file' : ''}`;
                
                const type = document.createElement('div');
                type.className = 'artifact-type';
                const typeText = document.createElement('strong');
                typeText.textContent = a.type;
                type.appendChild(typeText);
                
                const pathStr = document.createElement('div');
                pathStr.className = 'artifact-path';
                pathStr.textContent = a.path || 'Pending Upload';
                
                const status = document.createElement('div');
                status.className = 'artifact-status';
                status.textContent = a.status;
                
                const actionBtn = document.createElement('button');
                actionBtn.className = 'btn btn-secondary';
                actionBtn.style = 'margin-top: 10px; font-size: 0.8rem; padding: 4px 8px; width: 100%;';
                actionBtn.textContent = a.path ? 'Replace File' : 'Attach File';
                actionBtn.onclick = () => this.attachArtifact(a.artifact_id);

                const approval = document.createElement('select');
                approval.className = 'status-select';
                ['Draft', 'Review', 'Approved'].forEach(value => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value;
                    option.selected = a.status === value;
                    approval.appendChild(option);
                });
                approval.onchange = event => this.updateArtifactStatus(a.artifact_id, event.target.value);

                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn btn-secondary';
                removeBtn.style = 'font-size:0.8rem; padding:4px 8px; width:100%;';
                removeBtn.textContent = 'Remove Metadata';
                removeBtn.onclick = () => this.deleteArtifact(a.artifact_id, a.type);
                
                card.appendChild(type);
                card.appendChild(pathStr);
                card.appendChild(status);
                card.appendChild(approval);
                card.appendChild(actionBtn);
                card.appendChild(removeBtn);
                artContainer.appendChild(card);
            });
        }
    }

    async loadAuditLog() {
        const logs = await this.callBridge('get_audit', this.currentProject.id);
        const container = document.getElementById('audit-logs');
        container.innerHTML = '';
        logs.forEach(l => {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = l;
            container.appendChild(entry);
        });
    }

    analyzeProject() {
        // Reset modal state
        document.getElementById('ai-prompt-input').value = '';
        document.getElementById('ai-result-panel').classList.add('hidden');
        document.getElementById('ai-loading').classList.add('hidden');
        document.getElementById('ai-send-btn').disabled = false;
        document.getElementById('modal-ai-analyze').classList.remove('hidden');
    }

    setAiPrompt(text) {
        document.getElementById('ai-prompt-input').value = text;
    }

    async submitAiAnalyze() {
        const promptText = document.getElementById('ai-prompt-input').value.trim();
        if (!promptText) {
            this.showToast('Please enter a prompt or select a quick prompt.', 'warning');
            return;
        }

        const preview = await this.callBridge('preview_ai_request', {
            project_id: this.currentProject.id,
            prompt: promptText
        });
        const previewText = `${preview.warning}\n\nProvider: ${preview.provider}\nModel: ${preview.model}\nSize: ${preview.characters} characters\n\n${preview.payload_preview}`;
        if (!window.confirm(`${previewText}\n\nSend this redacted payload?`)) return;

        // Show loading, hide result, disable button
        document.getElementById('ai-loading').classList.remove('hidden');
        document.getElementById('ai-result-panel').classList.add('hidden');
        document.getElementById('ai-send-btn').disabled = true;

        try {
            const res = await this.callBridge('analyze_project', {
                project_id: this.currentProject.id,
                prompt: promptText
            });

            const resultContent = document.getElementById('ai-result-content');
            resultContent.textContent = res.result || 'No response.';
            document.getElementById('ai-result-panel').classList.remove('hidden');
        } catch (e) {
            // Error toast already handled by callBridge
        } finally {
            document.getElementById('ai-loading').classList.add('hidden');
            document.getElementById('ai-send-btn').disabled = false;
        }
    }
}

const app = new App();

window.addEventListener('pywebviewready', () => {
    app.init();
});
