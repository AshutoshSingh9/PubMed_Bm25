import os
import json
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8060

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antigravity Testing Dashboard</title>
    <style>
        :root {
            --bg-color: #000000;
            --text-main: #ffffff;
            --text-muted: #888888;
            --accent: #ffffff;
            --border: rgba(255, 255, 255, 0.1);
            --card-bg: rgba(10, 10, 10, 0.4);
            --success: #00ff00;
            --error: #ff3333;
        }

        body, html {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
        }

        /* Three.js Canvas Container */
        #canvas-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
        }

        /* Minimalist UI */
        #ui-layer {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            box-sizing: border-box;
            overflow-y: auto;
        }

        .dashboard-container {
            max-width: 800px;
            width: 100%;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .header {
            text-align: left;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 400;
            margin: 0;
            letter-spacing: -0.5px;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 0.5rem;
            font-weight: 300;
        }

        .run-btn {
            background-color: transparent;
            color: var(--accent);
            border: 1px solid var(--border);
            padding: 0.6rem 1.5rem;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        .run-btn:hover {
            background-color: var(--accent);
            color: #000;
        }

        .run-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background-color: transparent;
            color: var(--text-muted);
            border-color: var(--border);
        }

        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
            margin-right: 8px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .results-area {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            min-height: 200px;
        }

        .summary-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }

        .stat-box {
            padding: 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            text-align: center;
        }

        .stat-box .value {
            font-size: 2rem;
            font-weight: 300;
            margin-bottom: 0.3rem;
        }

        .stat-box .label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .log-output {
            background: rgba(0,0,0,0.6);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            font-family: "JetBrains Mono", monospace, source-code-pro, Menlo, Monaco;
            font-size: 0.85rem;
            color: #ccc;
            white-space: pre-wrap;
            overflow-y: auto;
            max-height: 350px;
        }

        /* Syntax Highlight simplified */
        .color-pass { color: var(--success); }
        .color-fail { color: var(--error); }
        .color-info { color: #88ccff; }

    </style>
    <!-- Include Three.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>

    <div id="canvas-container"></div>

    <div id="ui-layer">
        <div class="dashboard-container">
            <div class="header">
                <div>
                    <h1>Testing Dashboard</h1>
                    <div class="subtitle">BioProj1 Diagnostic Pipeline Validation</div>
                </div>
                <button id="runBtn" class="run-btn" onclick="runTests()">Run Tests</button>
            </div>

            <div class="results-area">
                <div class="summary-stats">
                    <div class="stat-box">
                        <div class="value" id="totalPassed">-</div>
                        <div class="label color-pass">Passed</div>
                    </div>
                    <div class="stat-box">
                        <div class="value" id="totalFailed">-</div>
                        <div class="label color-fail">Failed</div>
                    </div>
                    <div class="stat-box">
                        <div class="value" id="timeElapsed">-</div>
                        <div class="label">Seconds</div>
                    </div>
                </div>

                <div class="log-output" id="logOutput">System Ready. Awaiting test execution...</div>
            </div>
        </div>
    </div>

    <script>
        // --- System Logic ---
        async function runTests() {
            const btn = document.getElementById('runBtn');
            const logOut = document.getElementById('logOutput');
            const passEl = document.getElementById('totalPassed');
            const failEl = document.getElementById('totalFailed');
            const timeEl = document.getElementById('timeElapsed');

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Running...';
            logOut.textContent = "Initializing test suite...";
            passEl.textContent = "-";
            failEl.textContent = "-";
            timeEl.textContent = "-";

            const startT = performance.now();

            try {
                const response = await fetch('/api/run_tests', { method: 'POST' });
                const data = await response.json();
                
                const passed = (data.output.match(/PASSED/g) || []).length;
                const failed = (data.output.match(/FAILED|ERROR/g) || []).length;
                
                passEl.textContent = passed;
                failEl.textContent = failed;
                
                let htmlOut = data.output
                    .replace(/</g, '&lt;').replace(/>/g, '&gt;')
                    .replace(/(PASSED)/g, '<span class="color-pass">$1</span>')
                    .replace(/(FAILED|ERROR)/g, '<span class="color-fail">$1</span>')
                    .replace(/(collected \d+ items)/g, '<span class="color-info">$1</span>');
                
                logOut.innerHTML = htmlOut;

            } catch (err) {
                logOut.textContent = "Failed to communicate with test runner:\\n" + err.message;
            }

            const endT = performance.now();
            timeEl.textContent = ((endT - startT) / 1000).toFixed(2);

            btn.disabled = false;
            btn.innerHTML = 'Run Tests';
            
            // Scroll to bottom of logs
            logOut.scrollTop = logOut.scrollHeight;
        }

        // --- Three.js Back Dotted Waving Animation (Antigravity Style) ---
        // Antigravity minimalist aesthetic: black background, monochrome small dots waving softly
        const SEPARATION = 100, AMOUNTX = 50, AMOUNTY = 50;

        let container;
        let camera, scene, renderer;
        let particles, count = 0;
        let mouseX = 0, mouseY = 0;
        let windowHalfX = window.innerWidth / 2;
        let windowHalfY = window.innerHeight / 2;

        init();
        animate();

        function init() {
            container = document.getElementById('canvas-container');

            // Setup Camera
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 10000);
            camera.position.z = 1000;
            camera.position.y = 800;
            camera.position.x = 200;

            scene = new THREE.Scene();

            // Setup Particles
            const numParticles = AMOUNTX * AMOUNTY;
            const positions = new Float32Array(numParticles * 3);
            const scales = new Float32Array(numParticles);

            let i = 0, j = 0;
            for (let ix = 0; ix < AMOUNTX; ix++) {
                for (let iy = 0; iy < AMOUNTY; iy++) {
                    positions[i] = ix * SEPARATION - ((AMOUNTX * SEPARATION) / 2); // x
                    positions[i + 1] = 0; // y
                    positions[i + 2] = iy * SEPARATION - ((AMOUNTY * SEPARATION) / 2) - 1000; // z
                    scales[j] = 1;
                    i += 3;
                    j++;
                }
            }

            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('scale', new THREE.BufferAttribute(scales, 1));

            // Custom shader for dynamic scaling dots
            const material = new THREE.ShaderMaterial({
                uniforms: {
                    color: { value: new THREE.Color(0xffffff) }
                },
                vertexShader: `
                    attribute float scale;
                    void main() {
                        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                        gl_PointSize = scale * (150.0 / -mvPosition.z);
                        gl_Position = projectionMatrix * mvPosition;
                    }
                `,
                fragmentShader: `
                    uniform vec3 color;
                    void main() {
                        if (length(gl_PointCoord - vec2(0.5, 0.5)) > 0.475) discard;
                        gl_FragColor = vec4(color, 0.4);
                    }
                `,
                transparent: true,
                depthWrite: false
            });

            particles = new THREE.Points(geometry, material);
            scene.add(particles);

            // Renderer Setup
            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setClearColor(0x000000, 1);
            container.appendChild(renderer.domElement);

            document.addEventListener('mousemove', onDocumentMouseMove);
            window.addEventListener('resize', onWindowResize);
        }

        function onWindowResize() {
            windowHalfX = window.innerWidth / 2;
            windowHalfY = window.innerHeight / 2;
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function onDocumentMouseMove(event) {
            mouseX = event.clientX - windowHalfX;
            mouseY = event.clientY - windowHalfY;
        }

        function animate() {
            requestAnimationFrame(animate);
            render();
        }

        function render() {
            camera.position.x += (mouseX*2 - camera.position.x) * 0.05;
            camera.position.y += (-mouseY*2 + 400 - camera.position.y) * 0.05;
            camera.lookAt(scene.position);

            const positions = particles.geometry.attributes.position.array;
            const scales = particles.geometry.attributes.scale.array;

            let i = 0, j = 0;
            for (let ix = 0; ix < AMOUNTX; ix++) {
                for (let iy = 0; iy < AMOUNTY; iy++) {
                    positions[i + 1] = (Math.sin((ix + count) * 0.3) * 50) +
                                       (Math.sin((iy + count) * 0.5) * 50);
                    scales[j] = (Math.sin((ix + count) * 0.3) + 1) * 6 +
                                (Math.sin((iy + count) * 0.5) + 1) * 6;
                    i += 3;
                    j++;
                }
            }

            particles.geometry.attributes.position.needsUpdate = true;
            particles.geometry.attributes.scale.needsUpdate = true;

            renderer.render(scene, camera);
            count += 0.08;
        }
    </script>
</body>
</html>
"""

class TestDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/run_tests':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                # Run pytest in the background and capture output
                result = subprocess.run(
                    [os.sys.executable, "-m", "pytest", "-v", "tests/"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                output = result.stdout
                if not output:
                    output = result.stderr
                    
                response_data = {
                    "status": "success" if result.returncode == 0 else "failed",
                    "output": output
                }
            except Exception as e:
                response_data = {
                    "status": "error",
                    "output": f"Exception occurred while running tests: {str(e)}"
                }
                
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, TestDashboardHandler)
    print(f"🚀 Testing Dashboard running gracefully on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server shutdown.")

if __name__ == '__main__':
    run_server()
