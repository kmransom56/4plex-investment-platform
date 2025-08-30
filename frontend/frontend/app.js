// public/app.js
// Main topology editor + PDF & Visio integration

// Initialize app when dependencies are loaded
window.initApp = function() {
  if (!window.dependenciesLoaded) {
    console.warn('Dependencies not yet loaded, waiting...');
    return;
  }
  
  if (!window.THREE) {
    console.error('THREE.js not loaded');
    return;
  }
  
  console.log('Initializing 3D Network Topology Editor...');
  // 1. Three.js setup
  const canvas = document.getElementById('topo-canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1116);
  const camera = new THREE.PerspectiveCamera(60, 2, 0.1, 2000);
  camera.position.set(0, 80, 150);
  
  // Enhanced lighting
  scene.add(new THREE.AmbientLight(0xffffff, 0.85));
  const dir = new THREE.DirectionalLight(0xffffff, 0.6);
  dir.position.set(50, 100, 50);
  scene.add(dir);
  
  // Enhanced grid with color theming
  const grid = new THREE.GridHelper(200, 100, 0x30363d, 0x20262d);
  scene.add(grid);
  
  // Orbit controls (check if available)
  let controls;
  if (THREE.OrbitControls) {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
  } else {
    console.warn('OrbitControls not loaded, using manual camera controls');
  }
  
  // Mouse interaction setup
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const planeIntersect = new THREE.Vector3();
  
  let dragging = null;
  let offset = new THREE.Vector3();
  
  // Device materials by type
  const materialByType = {
    router: new THREE.MeshStandardMaterial({ color: 0x3fb950 }),
    switch: new THREE.MeshStandardMaterial({ color: 0x58a6ff }),
    firewall: new THREE.MeshStandardMaterial({ color: 0xf0883e }),
    access_point: new THREE.MeshStandardMaterial({ color: 0xbf7af0 }),
    server: new THREE.MeshStandardMaterial({ color: 0xff6b6b }),
    default: new THREE.MeshStandardMaterial({ color: 0x9e9e9e })
  };
  
  const nodeGeometry = new THREE.BoxGeometry(8, 4, 8);
  const meshes = {}; // name -> THREE.Mesh for tracking

  function resize() {
    const { width, height } = canvas.getBoundingClientRect();
    renderer.setSize(width, height);
    camera.aspect = width/height;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
  }
  animate();
  
  // Mouse event handlers for drag-and-drop
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mousemove', onMouseMove);
  canvas.addEventListener('mouseup', onMouseUp);
  
  function onMouseDown(event) {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(scene.children.filter(obj => obj.userData.draggable));
    
    if (intersects.length > 0) {
      dragging = intersects[0].object;
      if (controls) controls.enabled = false;
      
      if (raycaster.ray.intersectPlane(plane, planeIntersect)) {
        offset.copy(planeIntersect).sub(dragging.position);
      }
    }
  }
  
  function onMouseMove(event) {
    if (!dragging) return;
    
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    
    if (raycaster.ray.intersectPlane(plane, planeIntersect)) {
      const target = new THREE.Vector3().copy(planeIntersect).sub(offset);
      target.x = Math.round(target.x / 5) * 5; // Snap to grid
      target.z = Math.round(target.z / 5) * 5;
      target.y = 5; // Keep at consistent height
      dragging.position.copy(target);
      updateYAML();
      updateConnectionPositions();
    }
  }
  
  function onMouseUp() {
    if (dragging) {
      // Clear any pending throttled updates
      if (onMouseMove.throttleTimer) {
        clearTimeout(onMouseMove.throttleTimer);
        onMouseMove.throttleTimer = null;
      }
      
      // Final update
      updateConnectionsForMesh(dragging);
      updateYAML();
      
      dragging = null;
      if (controls) controls.enabled = true;
    }
  }

  // 2. Asset drag & drop
  document.querySelectorAll('.asset-item').forEach(item => {
    item.addEventListener('dragstart', ev => ev.dataTransfer.setData('device-type', ev.target.dataset.type));
  });

  canvas.addEventListener('dragover', ev => ev.preventDefault());
  canvas.addEventListener('drop', async ev => {
    ev.preventDefault();
    const type = ev.dataTransfer.getData('device-type');
    const pos = screenToWorld(ev.clientX, ev.clientY);
    const name = `${type}_${Date.now()}`; // Generate unique name
    const mesh = await createDeviceMesh(type, name);
    mesh.position.copy(pos);
    scene.add(mesh);
    updateYAML();
  });

  function screenToWorld(x, y) {
    const rect = canvas.getBoundingClientRect();
    const nx = ((x - rect.left)/rect.width)*2 - 1;
    const ny = -((y - rect.top)/rect.height)*2 + 1;
    const vec = new THREE.Vector3(nx, ny, 0.5).unproject(camera);
    vec.x = Math.round(vec.x/10)*10;
    vec.y = 5;
    vec.z = Math.round(vec.z/10)*10;
    return vec;
  }

  // 3. Load model or billboard fallback with robust mesh tracking
  async function createDeviceMesh(type, name = null) {
    // Generate unique name if not provided
    if (!name) {
      name = generateUniqueName(type);
    } else {
      // Ensure name uniqueness
      name = ensureUniqueName(name);
    }
    
    // attempt GLB
    const glbUrl = `/models/${type}.glb`;
    let mesh;
    
    try {
      const res = await fetch(glbUrl, { method: 'HEAD' });
      if (res.ok) {
        mesh = await loadGlbMesh(glbUrl, type);
      } else {
        mesh = await makeBillboard(`/billboards/${type}.jpg`, type);
      }
    } catch (error) {
      console.warn(`Failed to load ${type} model:`, error);
      mesh = await createFallbackMesh(type);
    }
    
    // Set up mesh properties with guaranteed tracking
    mesh.userData.type = type;
    mesh.userData.name = name;
    mesh.userData.draggable = true;
    mesh.userData.id = `${type}_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    mesh.name = name;
    
    // Register in mesh tracking with validation
    registerMesh(name, mesh);
    
    return mesh;
  }
  
  function generateUniqueName(type) {
    let counter = 1;
    let baseName = `${type}_${counter}`;
    
    while (meshes[baseName]) {
      counter++;
      baseName = `${type}_${counter}`;
    }
    
    return baseName;
  }
  
  function ensureUniqueName(proposedName) {
    if (!meshes[proposedName]) {
      return proposedName;
    }
    
    let counter = 1;
    let uniqueName = `${proposedName}_${counter}`;
    
    while (meshes[uniqueName]) {
      counter++;
      uniqueName = `${proposedName}_${counter}`;
    }
    
    return uniqueName;
  }
  
  function registerMesh(name, mesh) {
    if (meshes[name]) {
      console.warn(`Mesh name collision detected: ${name}. Removing old mesh.`);
      const oldMesh = meshes[name];
      scene.remove(oldMesh);
      disposeMesh(oldMesh);
    }
    
    meshes[name] = mesh;
    console.log(`Registered mesh: ${name} (${mesh.userData.type})`);
  }
  
  function unregisterMesh(name) {
    if (meshes[name]) {
      delete meshes[name];
      console.log(`Unregistered mesh: ${name}`);
    }
  }
  
  async function createFallbackMesh(type) {
    const material = materialByType[type] || materialByType.default;
    const geometry = getGeometryForType(type);
    return new THREE.Mesh(geometry, material.clone());
  }

  // Enhanced GLB loader with material styling
  async function loadGlbMesh(_url, type) {
    try {
      // TODO: Implement actual GLTFLoader when available
      // const loader = new THREE.GLTFLoader();
      // const gltf = await new Promise((resolve, reject) => {
      //   loader.load(url, resolve, undefined, reject);
      // });
      // return gltf.scene.children[0];
      
      // For now, create styled geometry based on device type
      const material = materialByType[type] || materialByType.default;
      const geometry = getGeometryForType(type);
      const mesh = new THREE.Mesh(geometry, material.clone());
      
      // Add subtle emissive glow
      mesh.material.emissive = new THREE.Color(material.color).multiplyScalar(0.1);
      
      return mesh;
    } catch (error) {
      console.warn('GLB loading failed, using fallback:', error);
      const material = materialByType[type] || materialByType.default;
      return new THREE.Mesh(nodeGeometry, material.clone());
    }
  }
  
  function getGeometryForType(type) {
    switch (type) {
      case 'router':
        return new THREE.BoxGeometry(12, 4, 8);
      case 'switch':
        return new THREE.BoxGeometry(16, 2, 8);
      case 'firewall':
        return new THREE.BoxGeometry(10, 6, 10);
      case 'access_point':
        return new THREE.CylinderGeometry(4, 4, 2, 8);
      case 'server':
        return new THREE.BoxGeometry(8, 16, 12);
      default:
        return nodeGeometry;
    }
  }

  // billboard helper with type styling
  async function makeBillboard(url, type) {
    try {
      const tex = await new THREE.TextureLoader().loadAsync(url);
      const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true });
      const geo = new THREE.PlaneGeometry(12, 8);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.onBeforeRender = (_, __, camera) => mesh.quaternion.copy(camera.quaternion);
      return mesh;
    } catch (error) {
      console.warn('Billboard loading failed, using geometry fallback:', error);
      const material = materialByType[type] || materialByType.default;
      return new THREE.Mesh(nodeGeometry, material.clone());
    }
  }

  // 4. YAML sync and parsing
  const yamlOut = document.getElementById('yaml-output');
  
  function updateYAML() {
    const nodes = scene.children
      .filter(o => o.position && o.userData.type)
      .map(o => ({
        name: o.userData.name || o.userData.type,
        type: o.userData.type,
        position: {
          x: Math.round(o.position.x * 100) / 100,
          y: Math.round(o.position.y * 100) / 100,
          z: Math.round(o.position.z * 100) / 100
        }
      }));
    
    const topology = {
      nodes: nodes,
      connections: extractConnections()
    };
    
    const yamlString = generateYAMLString(topology);
    if (yamlOut) yamlOut.value = yamlString;
    
    // Auto-save to backend if configured
    if (window.autoSaveEnabled) {
      saveTopologyToBackend(topology);
    }
  }
  
  function generateYAMLString(topology) {
    let yaml = 'topology:\n';
    yaml += '  nodes:\n';
    
    topology.nodes.forEach(node => {
      yaml += `    - name: ${node.name}\n`;
      yaml += `      type: ${node.type}\n`;
      yaml += `      position:\n`;
      yaml += `        x: ${node.position.x}\n`;
      yaml += `        y: ${node.position.y}\n`;
      yaml += `        z: ${node.position.z}\n`;
    });
    
    if (topology.connections && topology.connections.length > 0) {
      yaml += '  connections:\n';
      topology.connections.forEach(conn => {
        yaml += `    - from: ${conn.from}\n`;
        yaml += `      to: ${conn.to}\n`;
        if (conn.type) yaml += `      type: ${conn.type}\n`;
      });
    }
    
    return yaml;
  }
  
  function extractConnections() {
    // TODO: Implement connection detection based on proximity or manual linking
    return [];
  }
  
  // YAML Parser: Convert YAML topology to 3D scene
  async function parseYAMLToScene(yamlString) {
    try {
      let topology;
      
      // Try using js-yaml library first (more robust)
      if (window.jsyaml) {
        try {
          const parsed = jsyaml.load(yamlString, {
            schema: jsyaml.SAFE_SCHEMA,
            json: true
          });
          topology = validateAndNormalizeTopology(parsed);
        } catch (yamlError) {
          console.warn('js-yaml parsing failed, falling back to custom parser:', yamlError);
          topology = parseYAMLString(yamlString);
        }
      } else {
        console.warn('js-yaml library not loaded, using custom parser');
        topology = parseYAMLString(yamlString);
      }
      
      await loadTopologyIntoScene(topology);
    } catch (error) {
      console.error('YAML parsing error:', error);
      alert('Failed to parse YAML: ' + error.message);
    }
  }
  
  function validateAndNormalizeTopology(parsed) {
    // Ensure the parsed object has the expected structure
    if (!parsed || typeof parsed !== 'object') {
      throw new Error('Invalid YAML: must be an object');
    }
    
    // Handle different possible root structures
    let topology = parsed;
    if (parsed.topology) {
      topology = parsed.topology;
    }
    
    // Ensure nodes array exists
    if (!topology.nodes) {
      topology.nodes = [];
    }
    
    if (!Array.isArray(topology.nodes)) {
      throw new Error('Nodes must be an array');
    }
    
    // Ensure connections array exists
    if (!topology.connections) {
      topology.connections = [];
    }
    
    if (!Array.isArray(topology.connections)) {
      throw new Error('Connections must be an array');
    }
    
    // Normalize node structure
    topology.nodes = topology.nodes.map((node, index) => {
      if (!node || typeof node !== 'object') {
        throw new Error(`Node at index ${index} must be an object`);
      }
      
      // Ensure required fields
      if (!node.type) {
        throw new Error(`Node at index ${index} is missing required 'type' field`);
      }
      
      // Generate name if missing
      if (!node.name) {
        node.name = `${node.type}_${index + 1}`;
      }
      
      // Normalize position
      if (node.position) {
        node.position = {
          x: parseFloat(node.position.x) || 0,
          y: parseFloat(node.position.y) || 5,
          z: parseFloat(node.position.z) || 0
        };
      }
      
      return node;
    });
    
    // Normalize connections
    topology.connections = topology.connections.filter((conn, index) => {
      if (!conn || typeof conn !== 'object') {
        console.warn(`Skipping invalid connection at index ${index}`);
        return false;
      }
      
      if (!conn.from || !conn.to) {
        console.warn(`Skipping connection at index ${index}: missing from/to`);
        return false;
      }
      
      return true;
    });
    
    return topology;
  }
  
  function parseYAMLString(yamlString) {
    try {
      // Fallback YAML parser for topology format (when js-yaml is not available)
      console.warn('Using fallback YAML parser - consider loading js-yaml library for better compatibility');
      
      const lines = yamlString.split('\n').map(line => line.replace(/\r$/, ''));
      const topology = { nodes: [], connections: [] };
      
      let currentSection = null;
      let currentNode = null;
      let currentConnection = null;
      // Reserved for future hierarchical parsing
      let _baseIndent = null; // TODO: implement hierarchical parsing based on indentation
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        
        // Skip empty lines and comments
        if (!trimmed || trimmed.startsWith('#')) continue;
        
        // Calculate indentation (handle both spaces and tabs)
        const leadingWhitespace = line.match(/^(\s*)/);
        const indent = leadingWhitespace ? leadingWhitespace[1].length : 0;
        
        try {
          if (trimmed.startsWith('topology:')) {
            _baseIndent = indent;
            continue;
          } else if (trimmed.startsWith('nodes:')) {
            currentSection = 'nodes';
            currentNode = null;
            currentConnection = null;
          } else if (trimmed.startsWith('connections:')) {
            currentSection = 'connections';
            currentNode = null;
            currentConnection = null;
          } else if (trimmed.startsWith('- ')) {
            // New list item
            if (currentSection === 'nodes') {
              currentNode = {};
              topology.nodes.push(currentNode);
            } else if (currentSection === 'connections') {
              currentConnection = {};
              topology.connections.push(currentConnection);
            }
            
            // Parse inline content after the dash
            const itemContent = trimmed.substring(2).trim();
            if (itemContent && itemContent.includes(':')) {
              const colonIndex = itemContent.indexOf(':');
              const key = itemContent.substring(0, colonIndex).trim();
              const value = itemContent.substring(colonIndex + 1).trim();
              
              if (currentNode && currentSection === 'nodes') {
                currentNode[key] = parseYAMLValue(value);
              } else if (currentConnection && currentSection === 'connections') {
                currentConnection[key] = parseYAMLValue(value);
              }
            }
          } else if (trimmed.includes(':')) {
            // Key-value pair
            const colonIndex = trimmed.indexOf(':');
            const key = trimmed.substring(0, colonIndex).trim();
            const value = trimmed.substring(colonIndex + 1).trim();
            
            if (currentSection === 'nodes' && currentNode) {
              if (key === 'position') {
                currentNode.position = {};
              } else if (currentNode.position && ['x', 'y', 'z'].includes(key)) {
                const numValue = parseFloat(value);
                currentNode.position[key] = isNaN(numValue) ? 0 : numValue;
              } else {
                currentNode[key] = parseYAMLValue(value);
              }
            } else if (currentSection === 'connections' && currentConnection) {
              currentConnection[key] = parseYAMLValue(value);
            }
          }
        } catch (lineError) {
          console.warn(`Error parsing YAML line ${i + 1}: "${line}"`, lineError);
          continue; // Skip problematic lines but continue parsing
        }
      }
      
      return validateAndNormalizeTopology({ topology });
      
    } catch (error) {
      console.error('Fallback YAML parsing failed:', error);
      throw new Error(`YAML parsing failed: ${error.message}`);
    }
  }
  
  function parseYAMLValue(value) {
    if (!value || value === '') return null;
    
    // Remove quotes
    const unquoted = value.replace(/^["']|["']$/g, '');
    
    // Handle boolean values
    if (unquoted.toLowerCase() === 'true') return true;
    if (unquoted.toLowerCase() === 'false') return false;
    if (unquoted.toLowerCase() === 'null' || unquoted.toLowerCase() === '~') return null;
    
    // Handle numbers
    const num = parseFloat(unquoted);
    if (!isNaN(num) && isFinite(num)) return num;
    
    // Return as string
    return unquoted;
  }
  
  // validateTopology has been replaced by validateAndNormalizeTopology
  // Removed to eliminate unused code warnings
  
  // This function is now replaced by parseYAMLValue above
  
  async function loadTopologyIntoScene(topology) {
    // Clear existing nodes
    clearScene();
    
    // Load nodes
    for (const nodeData of topology.nodes) {
      const mesh = await createDeviceMesh(nodeData.type, nodeData.name);
      
      if (nodeData.position) {
        mesh.position.set(
          nodeData.position.x || 0,
          nodeData.position.y || 5,
          nodeData.position.z || 0
        );
      } else {
        // Auto-layout if no position specified
        const index = topology.nodes.indexOf(nodeData);
        mesh.position.set(
          (index % 5) * 20 - 40,
          5,
          Math.floor(index / 5) * 20 - 40
        );
      }
      
      scene.add(mesh);
    }
    
    // TODO: Load connections as lines/curves between nodes
    if (topology.connections) {
      topology.connections.forEach(conn => {
        createConnection(conn.from, conn.to, conn.type);
      });
    }
    
    updateYAML();
  }
  
  function clearScene() {
    // Remove devices and connections
    const objectsToRemove = scene.children.filter(obj => 
      obj.userData.type || obj.userData.connection
    );
    
    objectsToRemove.forEach(obj => {
      scene.remove(obj);
      disposeMesh(obj);
    });
    
    // Clear mesh tracking
    Object.keys(meshes).forEach(key => {
      unregisterMesh(key);
    });
    
    console.log('Scene cleared successfully');
  }
  
  function disposeMesh(mesh) {
    if (mesh.geometry) {
      mesh.geometry.dispose();
    }
    
    if (mesh.material) {
      if (Array.isArray(mesh.material)) {
        mesh.material.forEach(mat => mat.dispose());
      } else {
        mesh.material.dispose();
      }
    }
    
    // Clean up any textures
    if (mesh.material && mesh.material.map) {
      mesh.material.map.dispose();
    }
  }
  
  function createConnection(fromName, toName, connectionType = 'ethernet') {
    try {
      const fromMesh = meshes[fromName];
      const toMesh = meshes[toName];
      
      if (!fromMesh) {
        console.warn(`Cannot create connection: source mesh '${fromName}' not found`);
        console.log('Available meshes:', Object.keys(meshes));
        return null;
      }
      
      if (!toMesh) {
        console.warn(`Cannot create connection: target mesh '${toName}' not found`);
        console.log('Available meshes:', Object.keys(meshes));
        return null;
      }
      
      // Remove existing connection between these nodes
      removeConnection(fromName, toName);
      
      const points = [
        fromMesh.position.clone(),
        toMesh.position.clone()
      ];
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({ 
        color: getConnectionColor(connectionType),
        linewidth: 2
      });
      
      const line = new THREE.Line(geometry, material);
      line.userData.connection = { 
        from: fromName, 
        to: toName, 
        type: connectionType,
        id: `${fromName}_to_${toName}`
      };
      line.name = `connection_${fromName}_to_${toName}`;
      
      scene.add(line);
      console.log(`Created connection: ${fromName} -> ${toName} (${connectionType})`);
      
      return line;
      
    } catch (error) {
      console.error(`Failed to create connection ${fromName} -> ${toName}:`, error);
      return null;
    }
  }
  
  function removeConnection(fromName, toName) {
    const connectionsToRemove = scene.children.filter(obj => 
      obj.userData.connection && 
      ((obj.userData.connection.from === fromName && obj.userData.connection.to === toName) ||
       (obj.userData.connection.from === toName && obj.userData.connection.to === fromName))
    );
    
    connectionsToRemove.forEach(connection => {
      scene.remove(connection);
      disposeMesh(connection);
    });
  }
  
  function updateConnectionPositions() {
    const connections = scene.children.filter(obj => obj.userData.connection);
    
    connections.forEach(connection => {
      updateSingleConnection(connection);
    });
  }
  
  function updateConnectionsForMesh(mesh) {
    if (!mesh.userData.name) return;
    
    const meshName = mesh.userData.name;
    const connections = scene.children.filter(obj => 
      obj.userData.connection && 
      (obj.userData.connection.from === meshName || obj.userData.connection.to === meshName)
    );
    
    connections.forEach(connection => {
      updateSingleConnection(connection);
    });
  }
  
  function updateSingleConnection(connection) {
    const { from, to } = connection.userData.connection;
    const fromMesh = meshes[from];
    const toMesh = meshes[to];
    
    if (fromMesh && toMesh) {
      // Calculate connection points with offset from device center
      const fromPoint = calculateConnectionPoint(fromMesh, toMesh);
      const toPoint = calculateConnectionPoint(toMesh, fromMesh);
      
      const points = [fromPoint, toPoint];
      
      // Update geometry efficiently
      const positions = connection.geometry.attributes.position;
      if (positions) {
        positions.setXYZ(0, fromPoint.x, fromPoint.y, fromPoint.z);
        positions.setXYZ(1, toPoint.x, toPoint.y, toPoint.z);
        positions.needsUpdate = true;
      } else {
        // Fallback: recreate geometry if positions array is missing
        connection.geometry.dispose();
        connection.geometry = new THREE.BufferGeometry().setFromPoints(points);
      }
    } else {
      console.warn(`Connection ${from} -> ${to} has missing mesh references`);
    }
  }
  
  function calculateConnectionPoint(fromMesh, toMesh) {
    const fromPos = fromMesh.position.clone();
    const toPos = toMesh.position.clone();
    
    // Calculate direction vector
    const direction = new THREE.Vector3().subVectors(toPos, fromPos).normalize();
    
    // Get mesh bounds to calculate edge offset
    const box = new THREE.Box3().setFromObject(fromMesh);
    const size = box.getSize(new THREE.Vector3());
    const maxDimension = Math.max(size.x, size.z) / 2;
    
    // Offset the connection point to the edge of the device
    return fromPos.clone().add(direction.multiplyScalar(maxDimension + 1));
  }
  
  function getConnectionColor(type) {
    const colorMap = {
      ethernet: 0x00ff00,
      fiber: 0xff6600,
      wireless: 0x0088ff,
      management: 0xff0088,
      default: 0xffffff
    };
    return colorMap[type] || colorMap.default;
  }
  
  async function saveTopologyToBackend(topology) {
    try {
      const response = await fetch('/api/topology/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(topology)
      });
      
      if (!response.ok) {
        console.warn('Failed to save topology to backend');
      }
    } catch (error) {
      console.warn('Error saving topology:', error);
    }
  }

  // 5. Status chips
  document.querySelectorAll('.status-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.status-chip').forEach(c=>c.classList.remove('active'));
      chip.classList.add('active');
      // TODO: POST /api/audit/log { status: chip.dataset.status }
    });
  });

  // 6. Generate Install PDF
  const btnGeneratePdf = document.getElementById('btn-generate-pdf');
  if (btnGeneratePdf) {
    btnGeneratePdf.addEventListener('click', async () => {
      const html = document.documentElement.outerHTML;
      const resp = await fetch('/api/pdf/generate', {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ jobId: 'JOB-'+Date.now(), html })
      });
      if (!resp.ok) return alert('PDF failed');
      const blob = await resp.blob();
      download(blob, 'install-pack.pdf');
      captureThumbnail();
    });
  }

  // 7. Import Visio (.vsdx)
  const btnImportVisio = document.getElementById('btn-import-visio');
  if (btnImportVisio) {
    btnImportVisio.addEventListener('click', () => {
      const inp = document.createElement('input');
      inp.type = 'file';
      inp.accept = '.vsdx';
      inp.onchange = async e => {
        const file = e.target.files[0];
        const form = new FormData();
        form.append('file', file);
        const r = await fetch('/api/visio/import', { method:'POST', body: form });
        const json = await r.json();
        if (json.success) {
          // place each node
          for (const n of json.nodes) {
            const mesh = await createDeviceMesh(n.type, n.name || `visio_${json.nodes.indexOf(n)}`);
            mesh.position.set(n.position[0], n.position[1], n.position[2]);
            scene.add(mesh);
          }
          updateYAML();
        }
      };
      inp.click();
    });
  }
  
  // 8. YAML Import/Export Controls
  const btnImportYaml = document.getElementById('btn-import-yaml');
  if (btnImportYaml) {
    btnImportYaml.addEventListener('click', () => {
      const inp = document.createElement('input');
      inp.type = 'file';
      inp.accept = '.yaml,.yml';
      inp.onchange = async e => {
        const file = e.target.files[0];
        const yamlContent = await file.text();
        await parseYAMLToScene(yamlContent);
      };
      inp.click();
    });
  }
  
  const btnExportYaml = document.getElementById('btn-export-yaml');
  if (btnExportYaml) {
    btnExportYaml.addEventListener('click', () => {
      const yamlContent = yamlOut?.value || generateYAMLString({
        nodes: scene.children
          .filter(o => o.position && o.userData.type)
          .map(o => ({
            name: o.userData.name || o.userData.type,
            type: o.userData.type,
            position: {
              x: Math.round(o.position.x * 100) / 100,
              y: Math.round(o.position.y * 100) / 100,
              z: Math.round(o.position.z * 100) / 100
            }
          })),
        connections: []
      });
      
      const blob = new Blob([yamlContent], { type: 'text/yaml' });
      download(blob, `topology_${new Date().toISOString().split('T')[0]}.yaml`);
    });
  }
  
  const btnLoadYamlFromInput = document.getElementById('btn-load-yaml');
  if (btnLoadYamlFromInput && yamlOut) {
    btnLoadYamlFromInput.addEventListener('click', async () => {
      const yamlContent = yamlOut.value;
      if (yamlContent.trim()) {
        await parseYAMLToScene(yamlContent);
      } else {
        alert('Please enter YAML content first');
      }
    });
  }
  
  const btnClearScene = document.getElementById('btn-clear-scene');
  if (btnClearScene) {
    btnClearScene.addEventListener('click', () => {
      if (confirm('Clear all devices from the scene?')) {
        clearScene();
        updateYAML();
      }
    });
  }
  
  // 9. Auto-layout button
  const btnAutoLayout = document.getElementById('btn-auto-layout');
  if (btnAutoLayout) {
    btnAutoLayout.addEventListener('click', () => {
      autoLayoutDevices();
    });
  }
  
  function autoLayoutDevices() {
    const devices = scene.children.filter(obj => obj.userData.type);
    const gridSize = Math.ceil(Math.sqrt(devices.length));
    const spacing = 25;
    
    devices.forEach((device, index) => {
      const row = Math.floor(index / gridSize);
      const col = index % gridSize;
      const x = (col - gridSize / 2) * spacing;
      const z = (row - gridSize / 2) * spacing;
      
      device.position.set(x, 5, z);
    });
    
    updateYAML();
  }

  // helpers
  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  // 8. Thumbnail preview
  function captureThumbnail() {
    const data = canvas.toDataURL('image/jpeg', 0.8);
    document.getElementById('thumb-img').src = data;
  }
};

// Fallback: initialize on DOMContentLoaded if dependencies are already loaded
document.addEventListener('DOMContentLoaded', () => {
  if (window.dependenciesLoaded) {
    window.initApp();
  }
});
