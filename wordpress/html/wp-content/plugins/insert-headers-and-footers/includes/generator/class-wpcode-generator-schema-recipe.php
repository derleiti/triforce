<?php
/**
 * Generate a snippet for Recipe schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Recipe class.
 */
class WPCode_Generator_Schema_Recipe extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-recipe';

	/**
	 * The categories for this generator.
	 *
	 * @var string[]
	 */
	public $categories = array(
		'schema',
	);

	/**
	 * Snippet code type for when it will be saved.
	 *
	 * @var string
	 */
	public $code_type = 'html';

	/**
	 * Set the translatable strings.
	 *
	 * @return void
	 */
	protected function set_strings() {
		$this->title       = __( 'Recipe Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for cooking recipes and food preparation instructions.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'         => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Recipe schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'general'      => array(
				'label'   => __( 'General', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Recipe Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the recipe.', 'insert-headers-and-footers' ),
							'id'              => 'name',
							'default'         => '',
							'predefined_tags' => array( 'title' ),
							'smart_tags'      => true,
							'placeholder'     => __( 'Classic Chocolate Chip Cookies', 'insert-headers-and-footers' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the recipe.', 'insert-headers-and-footers' ),
							'id'              => 'description',
							'default'         => '',
							'predefined_tags' => array( 'excerpt' ),
							'smart_tags'      => true,
							'placeholder'     => __( 'A delicious and easy-to-make chocolate chip cookie recipe that will become your family favorite.', 'insert-headers-and-footers' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Recipe Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the recipe image.', 'insert-headers-and-footers' ),
							'id'              => 'image',
							'placeholder'     => 'https://example.com/recipe-image.jpg',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Author Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the recipe author.', 'insert-headers-and-footers' ),
							'id'              => 'author_name',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
							'placeholder'     => __( 'John Smith', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Recipe Category', 'insert-headers-and-footers' ),
							'description' => __( 'The category of the recipe (salad, dessert).', 'insert-headers-and-footers' ),
							'id'          => 'recipe_category',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Dessert, Main Course, Appetizer', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Calories', 'insert-headers-and-footers' ),
							'description' => __( 'The calorie content of the recipe.', 'insert-headers-and-footers' ),
							'id'          => 'calories',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( '350 calories', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'textarea',
							'label'       => __( 'Ingredients', 'insert-headers-and-footers' ),
							'description' => __( 'List all ingredients, separated by commas.', 'insert-headers-and-footers' ),
							'id'          => 'ingredients',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( '2 cups all-purpose flour, 1 cup butter, 2 eggs, 1 cup sugar', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Recipe Cuisine', 'insert-headers-and-footers' ),
							'description' => __( 'The cuisine type (Italian, Mexican).', 'insert-headers-and-footers' ),
							'id'          => 'recipe_cuisine',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Italian, Mexican, Asian', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Prep Time', 'insert-headers-and-footers' ),
							'description' => __( 'Preparation time in ISO 8601 format (PT30M for 30 minutes).', 'insert-headers-and-footers' ),
							'id'          => 'prep_time',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'PT30M (30 minutes)', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Cook Time', 'insert-headers-and-footers' ),
							'description' => __( 'Cooking time in ISO 8601 format (PT1H for 1 hour).', 'insert-headers-and-footers' ),
							'id'          => 'cook_time',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'PT1H (1 hour)', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Total Time', 'insert-headers-and-footers' ),
							'description' => __( 'Total time in ISO 8601 format.', 'insert-headers-and-footers' ),
							'id'          => 'total_time',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'PT1H30M (1 hour 30 minutes)', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Recipe Yield', 'insert-headers-and-footers' ),
							'description' => __( 'Number of servings or yield amount.', 'insert-headers-and-footers' ),
							'id'          => 'recipe_yield',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( '4 servings', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'instructions' => array(
				'label'   => __( 'Instructions', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Instructions.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Step Name', 'insert-headers-and-footers' ),
							'description' => __( 'The name/title of this step.', 'insert-headers-and-footers' ),
							'id'          => 'instruction_name',
							'name'        => 'instruction_name[]',
							'repeater'    => 'instructions',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Preheat the oven', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'textarea',
							'label'       => __( 'Step Text', 'insert-headers-and-footers' ),
							'description' => __( 'The detailed instructions for this step.', 'insert-headers-and-footers' ),
							'id'          => 'instruction_text',
							'name'        => 'instruction_text[]',
							'repeater'    => 'instructions',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Preheat the oven to 350°F (175°C). Line a baking sheet with parchment paper.', 'insert-headers-and-footers' ),
							'rows'        => 4,
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Step Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of an image for this step.', 'insert-headers-and-footers' ),
							'id'              => 'instruction_image',
							'name'            => 'instruction_image[]',
							'repeater'        => 'instructions',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/step-image.jpg',
							'default'         => '',
							'is_image_url'    => true,
						),
					),
					// Column 2 - Repeater button.
					array(
						array(
							'type'        => 'repeater_button',
							'id'          => 'instructions',
							'button_text' => __( 'Add Another Step', 'insert-headers-and-footers' ),
						),
					),
				),
			),
		);
	}

	/**
	 * Generate the snippet code without processing smart tags.
	 *
	 * @return string
	 */
	protected function generate_snippet_code() {
		$schema = array(
			'@context'    => 'https://schema.org',
			'@type'       => 'Recipe',
			'name'        => $this->get_value( 'name' ),
			'description' => $this->get_value( 'description' ),
		);

		// Add author if provided.
		$author_name = $this->get_value( 'author_name' );
		if ( ! empty( $author_name ) ) {
			$schema['author'] = array(
				'@type' => 'Person',
				'name'  => $author_name,
			);
		}

		// Add image if provided.
		$image = $this->get_value( 'image' );
		if ( ! empty( $image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image,
			);
		}

		// Add recipe category if provided.
		$recipe_category = $this->get_value( 'recipe_category' );
		if ( ! empty( $recipe_category ) ) {
			$schema['recipeCategory'] = $recipe_category;
		}

		// Add recipe cuisine if provided.
		$recipe_cuisine = $this->get_value( 'recipe_cuisine' );
		if ( ! empty( $recipe_cuisine ) ) {
			$schema['recipeCuisine'] = $recipe_cuisine;
		}

		// Add times if provided.
		$prep_time = $this->get_value( 'prep_time' );
		if ( ! empty( $prep_time ) ) {
			$schema['prepTime'] = $prep_time;
		}

		$cook_time = $this->get_value( 'cook_time' );
		if ( ! empty( $cook_time ) ) {
			$schema['cookTime'] = $cook_time;
		}

		$total_time = $this->get_value( 'total_time' );
		if ( ! empty( $total_time ) ) {
			$schema['totalTime'] = $total_time;
		}

		// Add recipe yield if provided.
		$recipe_yield = $this->get_value( 'recipe_yield' );
		if ( ! empty( $recipe_yield ) ) {
			$schema['recipeYield'] = $recipe_yield;
		}

		// Add nutrition if calories provided.
		$calories = $this->get_value( 'calories' );
		if ( ! empty( $calories ) ) {
			$schema['nutrition'] = array(
				'@type'    => 'NutritionInformation',
				'calories' => $calories,
			);
		}

		// Get the ingredients.
		$ingredients = $this->get_value( 'ingredients' );
		if ( ! empty( $ingredients ) ) {
			// Split by comma and trim each ingredient.
			$ingredients_array = array_map( 'trim', explode( ',', $ingredients ) );
			// Filter out empty values.
			$ingredients_array = array_filter( $ingredients_array );
			if ( ! empty( $ingredients_array ) ) {
				$schema['recipeIngredient'] = array_values( $ingredients_array );
			}
		}

		// Get the instructions.
		$instruction_names  = $this->get_value( 'instruction_name' );
		$instruction_texts  = $this->get_value( 'instruction_text' );
		$instruction_images = $this->get_value( 'instruction_image' );

		// If we have instructions, add them to the schema.
		if ( ! empty( $instruction_names ) && ! empty( $instruction_texts ) ) {
			// Convert to arrays if single values.
			if ( ! is_array( $instruction_names ) ) {
				$instruction_names = array( $instruction_names );
			}
			if ( ! is_array( $instruction_texts ) ) {
				$instruction_texts = array( $instruction_texts );
			}
			if ( ! is_array( $instruction_images ) ) {
				$instruction_images = array( $instruction_images );
			}

			$schema['recipeInstructions'] = array();

			// Add each instruction to the schema.
			foreach ( $instruction_names as $index => $instruction_name ) {
				if ( ! empty( $instruction_name ) && ! empty( $instruction_texts[ $index ] ) ) {
					$instruction = array(
						'@type' => 'HowToStep',
						'name'  => $instruction_name,
						'text'  => $instruction_texts[ $index ],
					);

					// Add image if provided.
					if ( ! empty( $instruction_images[ $index ] ) ) {
						$instruction['image'] = $instruction_images[ $index ];
					}

					$schema['recipeInstructions'][] = $instruction;
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
