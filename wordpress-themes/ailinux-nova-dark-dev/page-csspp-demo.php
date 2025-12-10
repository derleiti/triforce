<?php
/**
 * Template Name: CSS++ Demo Page
 *
 * Zeigt CSS++-Enhanced UI-Elemente
 *
 * @package Ailinux_Nova_Dark
 */

get_header();
?>

<main id="primary" class="site-main">
	<div class="container" style="max-width: 1200px; margin: 0 auto; padding: var(--space-10) var(--space-6);">

		<!-- Header -->
		<div class="hero-csspp" style="margin-bottom: var(--space-12); text-align: center;">
			<h1 class="hero-csspp__title">CSS++ Live Demo</h1>
			<p style="font-size: 1.25rem; color: var(--muted); margin-top: var(--space-4);">
				Multisensorische UI-Elemente mit enhanced shadows, glow und Audio-Feedback
			</p>
		</div>

		<!-- Status Info -->
		<div style="background: var(--bg-1); padding: var(--space-6); border-radius: var(--radius-lg); margin-bottom: var(--space-10); border-left: 4px solid var(--accent-blue);">
			<h3 style="margin-top: 0;">✅ CSS++ Integration aktiv</h3>
			<p style="margin-bottom: 0.5rem;">
				<strong>Kompiliert:</strong> theme-enhancements.csspp → theme-enhancements.css
			</p>
			<p style="margin-bottom: 0;">
				<strong>Audio-Runtime:</strong>
				<?php if ( Ailinux_CSSPP_Integration::get_instance()->is_runtime_enabled() ) : ?>
					<span style="color: var(--accent-green);">✓ Aktiviert</span> (hover-sfx, click-sfx funktionieren)
				<?php else : ?>
					<span style="color: var(--muted);">○ Deaktiviert</span>
					<a href="<?php echo esc_url( admin_url( 'customize.php?autofocus[section]=csspp_settings' ) ); ?>" style="margin-left: 1rem; color: var(--accent-blue);">
						→ Im Customizer aktivieren
					</a>
				<?php endif; ?>
			</p>
		</div>

		<!-- Button Demos -->
		<section style="margin-bottom: var(--space-14);">
			<h2 style="margin-bottom: var(--space-6);">Enhanced Buttons</h2>

			<div style="display: flex; flex-wrap: wrap; gap: var(--space-4); margin-bottom: var(--space-6);">
				<button class="btn-csspp">
					Primary Button
				</button>

				<a href="#" class="btn-csspp" style="background: var(--accent-green); --accent-blue: var(--accent-green);">
					Success Button
				</a>

				<button class="btn-csspp" disabled style="opacity: 0.5; cursor: not-allowed;">
					Disabled Button
				</button>
			</div>

			<div style="background: var(--bg-2); padding: var(--space-4); border-radius: var(--radius-sm); font-family: var(--font-mono, monospace); font-size: 0.875rem;">
				<strong>CSS++ Features:</strong> shape: rounded-rect() | shadow-type: soft | glow-color | hover-sfx | click-sfx
			</div>
		</section>

		<!-- Card Demos -->
		<section style="margin-bottom: var(--space-14);">
			<h2 style="margin-bottom: var(--space-6);">Enhanced Cards</h2>

			<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--space-6);">
				<div class="card-csspp">
					<h3 style="margin-top: 0; color: var(--accent-blue);">Card 1</h3>
					<p>CSS++ generiert realistische Schatten mit der <code>depth: 0.3rem</code> Property.</p>
					<p style="margin-bottom: 0; color: var(--muted); font-size: 0.875rem;">
						Hover für verstärkten Effekt →
					</p>
				</div>

				<div class="card-csspp">
					<h3 style="margin-top: 0; color: var(--accent-green);">Card 2</h3>
					<p>Der Compiler wandelt <code>shadow-type: soft</code> in passende box-shadow-Werte um.</p>
					<p style="margin-bottom: 0; color: var(--muted); font-size: 0.875rem;">
						Keine Runtime nötig – pure CSS!
					</p>
				</div>

				<div class="card-csspp">
					<h3 style="margin-top: 0; color: var(--text);">Card 3</h3>
					<p>Kompatibel mit Theme-Variablen wie <code>--bg-1</code>, <code>--space-6</code>, <code>--radius-lg</code>.</p>
					<p style="margin-bottom: 0; color: var(--muted); font-size: 0.875rem;">
						Seamless integration ✓
					</p>
				</div>
			</div>
		</section>

		<!-- Navigation Demo -->
		<section style="margin-bottom: var(--space-14);">
			<h2 style="margin-bottom: var(--space-6);">Enhanced Navigation</h2>

			<nav class="nav-csspp" style="display: flex; gap: var(--space-2); background: var(--bg-1); padding: var(--space-4); border-radius: var(--radius-lg);">
				<a href="#">Home</a>
				<a href="#">About</a>
				<a href="#">Blog</a>
				<a href="#">Contact</a>
			</nav>

			<p style="margin-top: var(--space-4); color: var(--muted); font-size: 0.875rem;">
				<?php if ( Ailinux_CSSPP_Integration::get_instance()->is_runtime_enabled() ) : ?>
					🔊 Hover über Links → Chime-Sound (523Hz)
				<?php else : ?>
					Aktiviere Audio-Runtime für hover-sfx
				<?php endif; ?>
			</p>
		</section>

		<!-- Badge Demo -->
		<section style="margin-bottom: var(--space-14);">
			<h2 style="margin-bottom: var(--space-6);">Enhanced Badges</h2>

			<div style="display: flex; flex-wrap: wrap; gap: var(--space-3);">
				<span class="reading-time-csspp">
					<span>📖</span>
					<span>5 min read</span>
				</span>

				<span class="reading-time-csspp" style="--accent-green: #3b82f6; background: rgba(59, 130, 246, 0.1); color: #3b82f6;">
					<span>🏷️</span>
					<span>Tutorial</span>
				</span>

				<span class="reading-time-csspp" style="--accent-green: #f59e0b; background: rgba(245, 158, 11, 0.1); color: #f59e0b;">
					<span>⚡</span>
					<span>Featured</span>
				</span>
			</div>
		</section>

		<!-- Input Demo -->
		<section style="margin-bottom: var(--space-14);">
			<h2 style="margin-bottom: var(--space-6);">Enhanced Input</h2>

			<form style="max-width: 600px;">
				<div style="margin-bottom: var(--space-4);">
					<label for="demo-input" style="display: block; margin-bottom: var(--space-2); font-weight: 600;">
						Dein Name
					</label>
					<input
						type="text"
						id="demo-input"
						class="input-csspp"
						placeholder="Gib deinen Namen ein..."
					/>
					<p style="margin-top: var(--space-2); color: var(--muted); font-size: 0.875rem;">
						<?php if ( Ailinux_CSSPP_Integration::get_instance()->is_runtime_enabled() ) : ?>
							🔊 Focus → Chime-Sound (880Hz)
						<?php else : ?>
							Aktiviere Audio-Runtime für focus-sfx
						<?php endif; ?>
					</p>
				</div>

				<button type="submit" class="btn-csspp">
					Submit
				</button>
			</form>
		</section>

		<!-- How it Works -->
		<section style="background: var(--bg-1); padding: var(--space-8); border-radius: var(--radius-lg);">
			<h2 style="margin-top: 0;">Wie funktioniert CSS++?</h2>

			<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: var(--space-6);">
				<div>
					<h3 style="color: var(--accent-blue);">1. Schreiben</h3>
					<pre style="background: var(--bg-2); padding: var(--space-3); border-radius: var(--radius-sm); overflow-x: auto; font-size: 0.8rem;"><code>.btn-csspp {
  shadow-type: soft;
  glow-color: var(--accent-blue);
  hover-sfx: chime(440Hz);
}</code></pre>
				</div>

				<div>
					<h3 style="color: var(--accent-green);">2. Kompilieren</h3>
					<pre style="background: var(--bg-2); padding: var(--space-3); border-radius: var(--radius-sm); overflow-x: auto; font-size: 0.8rem;"><code>npm run csspp:compile

→ theme-enhancements.css
→ theme-enhancements.assets.json</code></pre>
				</div>

				<div>
					<h3 style="color: var(--text);">3. Verwenden</h3>
					<pre style="background: var(--bg-2); padding: var(--space-3); border-radius: var(--radius-sm); overflow-x: auto; font-size: 0.8rem;"><code>// functions.php
wp_enqueue_style(
  'csspp-theme',
  '...theme-enhancements.css'
);</code></pre>
				</div>
			</div>

			<p style="margin-top: var(--space-6); margin-bottom: 0; color: var(--muted);">
				<strong>Keine Installation nötig:</strong> Kompiliertes CSS funktioniert in jedem Browser.
				Audio-Runtime ist optional (4KB JavaScript).
			</p>
		</section>

	</div>
</main>

<?php
get_footer();
