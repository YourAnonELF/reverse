document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const input = document.getElementById('target-input');
    const errorMsg = document.getElementById('error-msg');
    const loader = document.getElementById('loader');
    const resultsSec = document.getElementById('results');
    const copyBtn = document.getElementById('copy-btn');

    const elTarget = document.getElementById('res-target');
    const elIp = document.getElementById('res-ip');
    const elTotal = document.getElementById('res-total');
    const elTime = document.getElementById('res-time');
    const elSourcesList = document.getElementById('sources-list');
    const elDomainsList = document.getElementById('domains-list');

    let currentDomains = [];
    const reactiveBound = new WeakSet();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const target = input.value.trim();
        if (!target) return;

        errorMsg.classList.add('hidden');
        resultsSec.classList.add('hidden');
        loader.classList.remove('hidden');

        try {
            const res = await fetch(`/api/lookup?target=${encodeURIComponent(target)}`);
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'An error occurred during lookup.');
            }

            renderResults(data);
        } catch (err) {
            errorMsg.textContent = err.message;
            errorMsg.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });

    function renderResults(data) {
        loader.classList.add('hidden');

        elTarget.textContent = data.target;
        elIp.textContent = data.ip;
        elTotal.textContent = data.total.toString();
        elTime.textContent = `${data.elapsed_seconds}s`;

        elSourcesList.innerHTML = '';
        for (const [src, domains] of Object.entries(data.sources)) {
            const count = domains.length;
            const div = document.createElement('div');
            div.className = 'source-item';
            div.innerHTML = `
                <span class="source-name">${src}</span>
                <span class="source-count ${count === 0 ? 'zero' : ''}">${count}</span>
            `;
            elSourcesList.appendChild(div);
        }

        currentDomains = data.all_domains;
        elDomainsList.innerHTML = '';

        if (currentDomains.length === 0) {
            elDomainsList.innerHTML = `
                <tr>
                    <td colspan="2">
                        <div class="empty-state">
                            <i data-lucide="ghost"></i>
                            <p>No domains found for this target.</p>
                        </div>
                    </td>
                </tr>
            `;
            lucide.createIcons();
        } else {
            currentDomains.forEach((domain, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="col-idx">${idx + 1}</td>
                    <td>${domain}</td>
                `;
                elDomainsList.appendChild(tr);
            });
        }

        const revealTargets = resultsSec.querySelectorAll('.stat-card, .panel');
        revealTargets.forEach((el, idx) => {
            el.style.setProperty('--reveal-delay', `${Math.min(idx * 60, 320)}ms`);
            el.classList.add('fx-reveal');
        });

        resultsSec.classList.remove('hidden');
        resultsSec.classList.add('results-live');
        setupReactiveLighting(resultsSec);
    }

    copyBtn.addEventListener('click', () => {
        if (currentDomains.length === 0) return;

        const text = currentDomains.join('\n');
        navigator.clipboard.writeText(text).then(() => {
            const originalIcon = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i data-lucide="check"></i>';
            copyBtn.style.color = 'var(--md-sys-color-primary)';
            lucide.createIcons();

            setTimeout(() => {
                copyBtn.innerHTML = originalIcon;
                copyBtn.style.color = '';
                lucide.createIcons();
            }, 1800);
        });
    });

    function setupReactiveLighting(root = document) {
        const targets = root.querySelectorAll(
            '.search-box, button, .btn-icon, .search-box input, .panel, .panel-header, .stat-card, .source-item, .table-container, .domains-table th'
        );

        targets.forEach((el) => {
            if (reactiveBound.has(el)) return;
            reactiveBound.add(el);

            const isInput = el.tagName === 'INPUT';
            const isPanelLike = el.classList.contains('panel') || el.classList.contains('stat-card');
            el.classList.add(isInput ? 'reactive-field' : 'reactive-light');
            if (isPanelLike) {
                el.classList.add('reactive-panel');
            }

            el.style.setProperty('--mx', '50%');
            el.style.setProperty('--my', '50%');

            el.addEventListener('pointerenter', () => {
                el.style.setProperty('--glow-opacity', isPanelLike ? '0.92' : '1');
            });

            el.addEventListener('pointerleave', () => {
                el.style.setProperty('--glow-opacity', '0');
            });

            el.addEventListener('pointermove', (evt) => {
                const rect = el.getBoundingClientRect();
                const x = evt.clientX - rect.left;
                const y = evt.clientY - rect.top;
                el.style.setProperty('--mx', `${x}px`);
                el.style.setProperty('--my', `${y}px`);
            });
        });
    }

    function setupMatrixRain() {
        const canvas = document.getElementById('matrix-bg');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const columnWidth = 32;
        const droplets = [];
        const lights = [];

        let width = 0;
        let height = 0;
        let columns = 0;
        let streams = [];
        let heartSprite = null;
        let dropletSprite = null;

        function iconToSvgMarkup(name, color, size) {
            const icon = window.lucide?.icons?.[name];
            if (!icon) return null;

            if (typeof icon.toSvg === 'function') {
                return icon.toSvg({
                    width: size,
                    height: size,
                    color,
                    'stroke-width': 2.1,
                    'stroke-linecap': 'round',
                    'stroke-linejoin': 'round'
                });
            }

            if (Array.isArray(icon.iconNode)) {
                const nodes = icon.iconNode
                    .map(([tag, attrs]) => {
                        const attrsText = Object.entries(attrs)
                            .map(([k, v]) => `${k}="${v}"`)
                            .join(' ');
                        return `<${tag} ${attrsText}></${tag}>`;
                    })
                    .join('');
                return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">${nodes}</svg>`;
            }

            return null;
        }

        function loadSvgImage(svgMarkup) {
            return new Promise((resolve) => {
                if (!svgMarkup) {
                    resolve(null);
                    return;
                }

                const img = new Image();
                img.onload = () => resolve(img);
                img.onerror = () => resolve(null);
                img.src = `data:image/svg+xml;utf8,${encodeURIComponent(svgMarkup)}`;
            });
        }

        function createStream() {
            return {
                xJitter: (Math.random() - 0.5) * 10,
                y: Math.random() * -height,
                speed: 2 + Math.random() * 2.3,
                alpha: 0.5 + Math.random() * 0.34,
                size: 16 + Math.random() * 8,
                trailInterval: 3 + Math.floor(Math.random() * 4),
                tick: Math.floor(Math.random() * 5),
                pulse: Math.random() * Math.PI * 2
            };
        }

        function addLight(x, y, radius, alpha, tone = 'heart') {
            lights.push({ x, y, radius, alpha, life: 1, tone });
        }

        function createDroplet(x, y) {
            droplets.push({
                x,
                y,
                size: 9 + Math.random() * 6,
                vy: 0.7 + Math.random() * 1.1,
                alpha: 0.34 + Math.random() * 0.28,
                life: 16 + Math.floor(Math.random() * 14)
            });
        }

        function drawSprite(sprite, x, y, size, alpha, rotation = 0) {
            if (!sprite) return false;
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(rotation);
            ctx.globalAlpha = alpha;
            ctx.drawImage(sprite, -size / 2, -size / 2, size, size);
            ctx.restore();
            return true;
        }

        function drawLightingLayer() {
            ctx.save();
            ctx.globalCompositeOperation = 'screen';

            for (let i = lights.length - 1; i >= 0; i -= 1) {
                const light = lights[i];
                light.life *= 0.88;
                light.alpha *= 0.9;
                light.radius *= 1.02;

                const grad = ctx.createRadialGradient(light.x, light.y, 0, light.x, light.y, light.radius);
                const inner = light.tone === 'tear' ? `rgba(131, 205, 255, ${Math.min(light.alpha, 0.5)})` : `rgba(255, 167, 188, ${Math.min(light.alpha, 0.62)})`;
                const outer = light.tone === 'tear' ? `rgba(41, 109, 186, ${light.alpha * 0.14})` : `rgba(128, 23, 63, ${light.alpha * 0.16})`;
                grad.addColorStop(0, inner);
                grad.addColorStop(0.45, outer);
                grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(light.x, light.y, light.radius, 0, Math.PI * 2);
                ctx.fill();

                if (light.life < 0.06 || light.alpha < 0.02) {
                    lights.splice(i, 1);
                }
            }

            ctx.restore();
        }

        function resize() {
            const dpr = Math.max(window.devicePixelRatio || 1, 1);
            width = window.innerWidth;
            height = window.innerHeight;

            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            columns = Math.ceil(width / columnWidth);
            streams = Array.from({ length: columns }, createStream);
            droplets.length = 0;
            lights.length = 0;

            ctx.fillStyle = '#14131c';
            ctx.fillRect(0, 0, width, height);
        }

        function drawFrame() {
            ctx.fillStyle = 'rgba(20, 19, 28, 0.42)';
            ctx.fillRect(0, 0, width, height);

            ctx.textAlign = 'center';
            const heartVisibility = 0;

            for (let i = 0; i < streams.length; i += 1) {
                const stream = streams[i];
                const x = i * columnWidth + (columnWidth * 0.5) + stream.xJitter;
                const pulseStrength = 0.85 + Math.sin(stream.pulse) * 0.15;
                stream.pulse += 0.06;
                stream.tick += 1;

                if (stream.tick % stream.trailInterval === 0) {
                    createDroplet(x + (Math.random() - 0.5) * 10, stream.y + stream.size * 0.45);
                    if (Math.random() < 0.28) {
                        createDroplet(x + (Math.random() - 0.5) * 16, stream.y + stream.size * 0.8);
                    }
                }

                addLight(x, stream.y, 54 + stream.size * 1.8, 0.13 * pulseStrength, 'heart');

                if (heartVisibility > 0) {
                    drawSprite(
                        heartSprite,
                        x,
                        stream.y,
                        stream.size * 1.2,
                        Math.min(stream.alpha * 0.52, 0.46) * pulseStrength * heartVisibility,
                        Math.sin(stream.pulse * 0.45) * 0.08
                    );
                }

                stream.y += stream.speed;
                if (stream.y > height + 40) {
                    streams[i] = createStream();
                }
            }

            for (let i = droplets.length - 1; i >= 0; i -= 1) {
                const d = droplets[i];
                d.y += d.vy;
                d.alpha *= 0.9;
                d.life -= 1;

                addLight(d.x, d.y, d.size * 3.2, d.alpha * 0.2, 'tear');

                const drawn = drawSprite(dropletSprite, d.x, d.y, d.size, Math.min(d.alpha + 0.1, 0.82));
                if (!drawn) {
                    ctx.fillStyle = `rgba(128, 206, 255, ${Math.min(d.alpha + 0.12, 0.92)})`;
                    ctx.beginPath();
                    ctx.arc(d.x, d.y, d.size * 0.28, 0, Math.PI * 2);
                    ctx.fill();
                }

                if (d.life <= 0 || d.alpha < 0.03 || d.y > height + 20) {
                    droplets.splice(i, 1);
                }
            }

            drawLightingLayer();
            requestAnimationFrame(drawFrame);
        }

        async function initSprites() {
            const [heartImg, dropletImg] = await Promise.all([
                loadSvgImage(iconToSvgMarkup('heart-crack', 'rgba(255,158,180,0.55)', 72)),
                loadSvgImage(iconToSvgMarkup('droplet', '#8fd6ff', 64))
            ]);
            heartSprite = heartImg;
            dropletSprite = dropletImg;
        }

        window.addEventListener('resize', resize);
        resize();
        initSprites().finally(() => {
            requestAnimationFrame(drawFrame);
        });
    }

    setupReactiveLighting();
    setupMatrixRain();
});
