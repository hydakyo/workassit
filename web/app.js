const API_BASE = 'http://localhost:8000/api';

class App {
    constructor() {
        this.currentProject = null;
        this.projects = [];
        this.init();
    }

    async init() {
        this.setupNavigation();
        this.setupTabs();
        await this.loadSettings();
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
        toast.innerHTML = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // API Calls
    async fetchAPI(endpoint, options = {}) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'API Error');
            }
            return await res.json();
        } catch (err) {
            this.showToast(err.message, 'error');
            throw err;
        }
    }

    async loadSettings() {
        try {
            const settings = await this.fetchAPI('/settings');
            document.getElementById('setting-theme').value = settings.theme;
            document.getElementById('setting-root').value = settings.workspace_roots[0] || '';
            document.getElementById('setting-ai-provider').value = settings.ai_provider;
            document.getElementById('setting-ai-key').value = settings.ai_api_key || '';
            
            // Apply theme
            if (settings.theme === 'dark') document.body.classList.add('dark');
            else document.body.classList.remove('dark');
        } catch (e) {}
    }

    async saveSettings() {
        const payload = {
            theme: document.getElementById('setting-theme').value,
            workspace_roots: [document.getElementById('setting-root').value],
            ai_provider: document.getElementById('setting-ai-provider').value,
            ai_api_key: document.getElementById('setting-ai-key').value
        };
        await this.fetchAPI('/settings', { method: 'POST', body: JSON.stringify(payload) });
        this.showToast('Settings saved successfully', 'success');
        this.loadSettings();
    }

    async scanProjects() {
        this.showToast('Scanning workspaces...');
        try {
            const res = await this.fetchAPI('/projects/scan');
            this.projects = res.projects;
            this.renderProjectsGrid();
            if (res.warnings.length) this.showToast('Scan completed with warnings', 'warning');
            else this.showToast('Scan completed', 'success');
        } catch (e) {}
    }

    renderProjectsGrid() {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = '';
        
        if (this.projects.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No workspaces found. Create one or sync your directory.</div>';
            return;
        }

        this.projects.forEach(p => {
            const card = document.createElement('div');
            card.className = 'project-card';
            card.onclick = () => this.openProject(p);
            
            const date = new Date(p.metadata.updated_at).toLocaleDateString();
            
            card.innerHTML = `
                <div class="card-header">
                    <div class="badge">${p.metadata.project_type}</div>
                </div>
                <div>
                    <h3>${p.metadata.project_name}</h3>
                    <div class="customer">${p.metadata.customer_name}</div>
                </div>
                <div class="card-footer">
                    <span>${p.metadata.stage}</span>
                    <span>Updated: ${date}</span>
                </div>
            `;
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
            project_type: document.getElementById('np-type').value
        };
        await this.fetchAPI('/projects', { method: 'POST', body: JSON.stringify(payload) });
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
        
        this.loadChecklist();
        this.loadAuditLog();
    }

    async importFile() {
        // In a real desktop app, we'd use an API to trigger a native file dialog.
        // For simplicity, we'll prompt the user for a path.
        const path = prompt('Enter absolute path of file to import:');
        if (!path) return;
        
        await this.fetchAPI('/projects/import', {
            method: 'POST', 
            body: JSON.stringify({ project_path: this.currentProject.path, file_path: path })
        });
        this.showToast('File imported', 'success');
        this.loadAuditLog();
    }

    async undoImport() {
        await this.fetchAPI('/projects/undo', {
            method: 'POST',
            body: JSON.stringify({ project_path: this.currentProject.path })
        });
        this.showToast('Undo successful', 'success');
        this.loadAuditLog();
    }

    async createPackage() {
        const res = await this.fetchAPI('/projects/package', {
            method: 'POST',
            body: JSON.stringify({ project_path: this.currentProject.path })
        });
        this.showToast(`Package created: ${res.path}`, 'success');
        this.loadAuditLog();
    }

    async loadChecklist() {
        const items = await this.fetchAPI(`/projects/checklist?project_path=${encodeURIComponent(this.currentProject.path)}`);
        const container = document.getElementById('checklist-items');
        container.innerHTML = '';
        
        items.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = `checklist-item ${item.is_completed ? 'completed' : ''}`;
            
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = item.is_completed;
            cb.onchange = async (e) => {
                items[index].is_completed = e.target.checked;
                await this.fetchAPI('/projects/checklist', {
                    method: 'POST',
                    body: JSON.stringify({ project_path: this.currentProject.path, items: items })
                });
                this.loadChecklist();
            };
            
            const content = document.createElement('div');
            content.className = 'checklist-content';
            content.innerHTML = `<strong>${item.title}</strong>`;
            
            div.appendChild(cb);
            div.appendChild(content);
            container.appendChild(div);
        });
    }

    async loadAuditLog() {
        const logs = await this.fetchAPI(`/projects/audit?project_path=${encodeURIComponent(this.currentProject.path)}`);
        const container = document.getElementById('audit-logs');
        container.innerHTML = logs.map(l => `<div class="log-entry">${l}</div>`).join('');
    }

    async analyzeProject() {
        const promptText = prompt('Enter analysis focus (e.g. security, structure):', 'General architectural review');
        if (!promptText) return;
        
        this.showToast('AI Analyzing... please wait');
        const res = await this.fetchAPI('/projects/analyze', {
            method: 'POST',
            body: JSON.stringify({ project_path: this.currentProject.path, prompt: promptText })
        });
        alert(res.result);
    }
}

const app = new App();
