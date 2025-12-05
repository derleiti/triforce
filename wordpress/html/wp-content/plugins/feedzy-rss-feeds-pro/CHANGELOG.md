#### [Version 3.1.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v3.0.2...v3.1.0) (2025-08-20)

### New Features

- Added debug logging system for better troubleshooting
- Custom cron schedules - create and manage custom import schedules (PRO)
- OpenAI model selection per action in the Importer for granular control
- URL-based filtering to exclude specific domains from feeds
- YouTube Shorts embedding support in imported posts
- Aspect ratio controls for thumbnail images
- Improved fallback image options per import job

### Improvements

- Major UI overhaul for the importer with tabbed interface and better organization
- Enhanced feed validation system
- Redesigned Dashboard (formerly Support page)
- Improved onboarding and import setup experience
- Better feed groups management interface
- More features available in the free version
- Added helper text for proxy and user-agent settings

### Bug Fixes

- Fixed categories settings changing when installing the PRO version
- Fixed action popup not closing when clicking outside
- Fixed HTML tags in post titles when using paraphrasing
- Fixed fallback images being ignored in classic block
- Fixed integration tab showing incorrect license status
- Fixed broken images in Feedzy Loop
- Fixed various UI alignment and layout issues

##### [Version 3.0.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v3.0.1...v3.0.2) (2025-04-07)

- Updated dependencies
- Fixed summary length issue with YouTube feeds
- Improved connection with OpenAI for import actions

##### [Version 3.0.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v3.0.0...v3.0.1) (2025-01-10)

- Fixed issue with Custom Fields not working in the import process

#### [Version 3.0.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.8...v3.0.0) (2025-01-06)

### New Features
- Auto-delete featured image after a number of days set up together with the post.
- Added the possibility to choose more, randomly selected fallback images for posts.
- Assign individual imports to specific authors (existing usernames) using the Feedzy UI.
- Allow actions to be used on custom fields in Feedzy import jobs. You can now translate, trim, search & replace, or even rephrase with AI custom fields that you import to your posts from different tags.
- Added the ability to export and upload import jobs. This feature helps with re-creating existing imports, transferring them to a different server where Feedzy is also used, and saves significant time.
- Global management for assigning imported posts to categories based on keywords used in titles with [#auto_categories].
- Added OpenRouter integration for enhanced connectivity, allowing users to utilize more large language models (LLMs) beyond OpenAI.
- Allowed cron settings to be configured per import job instead of globally.

### Improvements
- Improved filtering systems for the import process and the Feedzy Loop block. With robust filtering options, you can include items matching any condition, filter by fields like title, description, or custom fields, and use operators like contains, equals, or regex for precise control.
- Improved the way duplicates are removed during imports [Option to filter duplicates by magic tags].
- Simplified the translation user experience by incorporating translations into the action tags.
- Added more OpenAI models for enhanced selection options.
- Created a prompt for passing parameters to OpenAI to generate featured images more accurately.
- Moved the license key field from General Settings to Feedzy Settings for better accessibility.

### Bug Fixes
- Fixed the helper link to direct users to the correct OpenAI API key page.
- Fixed compatibility issues with certain third-party products when Feedzy External Image is used.
- Fixed a bug where content paraphrased with OpenAI returned quotes unexpectedly.
- Clarified that the PRO version requires the free plugin for seamless functionality.

##### [Version 2.4.8](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.7...v2.4.8) (2024-10-29)

Fixes
- Additional strings available for translation.
- Resolved UI issue with legacy magic tags in post title dropdown.

##### [Version 2.4.7](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.6...v2.4.7) (2024-07-01)

- Updated OpenAI model list
- Fixed missing images issue in Feedzy loop when used with Elementor

##### [Version 2.4.6](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.5...v2.4.6) (2024-05-30)

Improvements
- Improved compatibility with PHP 8.1
- Updated internal dependencies

Fixes
- Fixed issue with the fallback image per import job not working
- Fixed usage of custom tag for the featured image in the import settings

##### [Version 2.4.5](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.4...v2.4.5) (2024-04-01)

### Improvements
- **Updated internal dependencies**

##### [Version 2.4.4](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.3...v2.4.4) (2024-03-29)

### Fixes
- Updated internal dependencies
- Fixed issue with feed's featured image being overwritten by ChatGPT image generation even when present

##### [Version 2.4.3](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.2...v2.4.3) (2024-02-27)

### Fixes
- Reuse existing generated images before trying to generate new ones on import
- Updated dependencies

##### [Version 2.4.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.1...v2.4.2) (2024-02-02)

### Fixes
- Fixed dynamic category import issue

##### [Version 2.4.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.4.0...v2.4.1) (2024-01-29)

### Fixes
- Updated tested version of the Free plugin

#### [Version 2.4.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.3.2...v2.4.0) (2024-01-25)

### New Features
- Added an ability to generate featured images with OpenAI for imported posts

##### [Version 2.3.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.3.1...v2.3.2) (2024-01-12)

### Fixes
- Fixed missing title paraphrasing support for the Developer plan
- Enhanced security

##### [Version 2.3.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.3.0...v2.3.1) (2023-12-20)

### Improvements
- Added dropdown for OpenAI model
- Updated dependencies

### Bug Fixes
- Fixed "Post content" string from being imported when a YouTube Feed is used

#### [Version 2.3.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.5...v2.3.0) (2023-10-23)

### **New Features**

- **Paraphrasing using OpenAI / Chat GPT [PRO]:** This feature enables users to utilize OpenAI's Chat GPT for paraphrasing text. It can assist in rephrasing and generating alternative wording for content.
- **Content summarization support using OpenAI / Chat GPT  [PRO]:** With this feature, users can access support for summarizing longer pieces of content, making it easier to condense and understand the main points of a text.
- **Added support to create a dynamic category [PRO]:** Feedzy can now create WordPress categories automatically during the import by taking the category name from the RSS XML Feed.
- **Added individual fallback image setting [PRO]:** This feature allows users to set specific backup images for individual import jobs, not only a general fallback image for all import jobs.
- **Ability to trim content to a particular amount of characters:** Users can now trim or limit the length of content to a specified number of characters, helping to meet length requirements or constraints.
- **Integrated Search & Replace in the content of the tag feature:** This integration enables users to search for specific content within tags and replace it with alternative text, streamlining content management.
- **Added action chain process support:** This feature facilitates the creation of multiple actions for a single Feedzy magic tag. You can now add a tag for the import job and use multiple actions on it (_paraphrase, summarize, trim, etc._).

### **Bug Fixes**
- Fixed conflict with spintax support
- Fixed compatibility issue with the Elementor image rendering

##### [Version 2.2.5](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.4...v2.2.5) (2023-08-03)

- Fixed import custom field value issue with duplicate title

##### [Version 2.2.4](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.3...v2.2.4) (2023-07-06)

- Removed image tag escaping to fix issue with some images not displaying

##### [Version 2.2.3](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.2...v2.2.3) (2023-06-05)

- Updated dependencies

##### [Version 2.2.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.1...v2.2.2) (2023-03-31)

- Fixed the issue with extracting custom tags from YouTube feeds
- Removed composer Guzzle package dependency

##### [Version 2.2.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.2.0...v2.2.1) (2023-02-28)

* Fix Elementor query loop templates

#### [Version 2.2.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.1.0...v2.2.0) (2023-02-24)

### Fixes
- Update Guzzle version to solve various plugins conflicts
- Remove whitespace from the feed title
- Fix elementor deprecated errors
- Fix PHP 8 fatal error when importing custom tag
- Fix amazon integration support for developer license
- Fix compatibility with SpinnerChief's new API

#### [Version 2.1.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.5...v2.1.0) (2022-12-06)

### Features
- Add compatibility with Amazon Advertising API (https://docs.themeisle.com/article/1745-how-to-display-amazon-products-using-feedzy)
- Adds support for lazy loaded images on import

### Fixes
- Parsing custom tags at feed level does not work - extracts from item node
- Rephrasing full content does not consistently work
- Filtering content in Feedzy Loop available with Elementor Pro

##### [Version 2.0.5](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.4...v2.0.5) (2022-10-26)

* Fix keyword filtering not working on the full content text. 
* Fix full content filter is available as an option in Elementor's widget

##### [Version 2.0.4](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.3...v2.0.4) (2022-09-27)

- Fix custom tags that do not retrieve content if the Feedzy category is used instead of the URL of a feed
- Update dependencies

##### [Version 2.0.3](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.2...v2.0.3) (2022-09-09)

#### Fixes
- Fix paraphrasing on very long titles.
- Fix the forbidden icon on some Agency features.
- Fix spintax support on the personal plan
- Update dependencies

##### [Version 2.0.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.1...v2.0.2) (2022-07-22)

* Fix WordAI & SpinnerChief connection issue.

##### [Version 2.0.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v2.0.0...v2.0.1) (2022-07-19)

#### Fixes
* Fix import custom field value issue with underscore key

#### [Version 2.0.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.8.2...v2.0.0) (2022-07-14)

#### Features
- Adds Translation support on imported content.
- Adds built-in paraphrasing service.
- Adds Spintax text support.
- Major UI update to make the plugin much easier and cleaner to use.

#### Fixes
- Add support for data attributes
- Fix feedzy tags to display if the Elementor template is "Feedzy Loop"
- Fix date filter is not working with Feedzy Block

##### [Version 1.8.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.8.1...v1.8.2) (2022-01-28)

- Fix keyword filter issue with date filter
- Fix PHP notice regarding full content post
- Manipulate custom tag data

##### [Version 1.8.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.8.0...v1.8.1) (2021-12-20)

- Have a fallback for [#item_image]
- Conflict with Elementor editor
- Warnings when using Feedzy Elementor Widget and Elementor PRO
- Keyword Filtering when Excluding Posts

#### [Version 1.8.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.6...v1.8.0) (2021-10-19)

 - Adds compatibility for [Elementor Template Builder](https://docs.themeisle.com/article/1396-elementor-compatibility-in-feedzy) and Dynamic Tags support.
 - Adds compatibility [Enhanced keyword](https://docs.themeisle.com/article/1154-how-to-use-feed-to-post-feature-in-feedzy#filters) filtering support for grouping keywords with or/and
- Adds new global setting for deleting imported items
- Add more features to magic tags that allow exporting custom values from the feed
- Add filter by date and time support

##### [Version 1.7.6](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.5...v1.7.6) (2021-08-04)

Add wpautop tag support before import content
Fix feed import issue when use spinnerchief magic tags

##### [Version 1.7.5](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.4...v1.7.5) (2021-07-14)

* Fix WordAI rewrite content issue

##### [Version 1.7.4](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.3...v1.7.4) (2021-07-07)

- Fix WordAI compatibility with the new API
- Fix display feed item images issue in different feed template

##### [Version 1.7.3](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.2...v1.7.3) (2021-05-12)

* fix audio tag parsing
* fix display feed item images issues
* fix retrieve item custom tag value

##### [Version 1.7.2](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.1...v1.7.2) (2021-04-28)

* Fix save credentials issue for WordAI and SpinnerChief

##### [Version 1.7.1](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.7.0...v1.7.1) (2021-04-21)

* Fix broken language dropdown issue

#### [Version 1.7.0](https://github.com/Codeinwp/feedzy-rss-feeds-pro/compare/v1.6.14...v1.7.0) (2021-04-20)

### Fixes
* Fix randomness in custom tags retrieval
* Improve compatibility when Lite is not active and Pro version is
* Improve compatibility with latest PHP and WordPress versions

### v1.6.14 - 2020-12-25 
 **Changes:** 
 * [Feat] Support for using custom tags in the featured image field of the feed to post import
* [Fix] Exclude/include feed items based on keywords from the content
* [Fix] Incorrect import of custom tags, when keywords filters are used for feed to post import
 
 ### v1.6.13 - 2020-07-23 
 **Changes:** 
 * [Feat] Feed2Post - Add support for non-English text while extracting full content
* [Feat] Feed2Post - Update REST endpoint for full content import
* [Fix] Feed2Post - Missing Last Run Status option
 
 ### v1.6.12 - 2020-05-28 
 **Changes:** 
 * [Fix] TGMPA conflict with the Newspaper theme
* [Fix] Check Spinner Chief/WordAI account status before spinning
* [Fix] Error in parsing custom tags
* [Fix] Custom tags in ATOM feeds
 
 ### v1.6.11 - 2020-01-30 
 **Changes:** 
 * If feeds don't have images, inform the user instead of failing silently
* Add the ability to show the post author for imported posts both in frontend and backend
* Fix: Uncategorized is automatically added to all imported posts
* Fix: Additional Class(es) in Gutenberg were not used
* Fix: Youtube feed always shows summary even if summary is off in the shortcode
* Fix: Typo in tags available for use in the import to post feature
 
 ### v1.6.9 - 2019-12-13 
 **Changes:** 
 * Fix number of feed items to be imported defaults back to 10
* Fix widget to use all settings configured
* Add support for custom template tags
* Allow support for multiple taxonomies
 
 ### v1.6.8 - 2019-09-04 
 **Changes:** 
 * Add support to show featured image from a dynamic URL
* Full content to process only as many items as are being imported
* Add support to extract categories from feed
 
 ### v1.6.7 - 2019-07-24 
 **Changes:** 
 * Fix issue with delete posts created after X days deleting wrong data
 
 ### v1.6.6 - 2019-07-19 
 **Changes:** 
 * Show spinner while importing posts
* Fix issue with parsing custom tags
* Fix issue with custom fields getting wiped out when changing status of import
 
 ### v1.6.5 - 2019-05-30 
 **Changes:** 
 * fix: Posts not being assigned to taxonomy term when taxonomy name contains underscore
* feat: Auto delete posts after a specified time period
* feat: Referral URL now supports prefixes
 
 ### v1.6.4 - 2019-04-05 
 **Changes:** 
 * Add ability to spin full text content
* Extend custom magic tags to populate custom fields
 
 ### v1.6.3 - 2019-02-05 
 **Changes:** 
 * Fix issues with post title created by WordAI and SpinnerChief
* Fix issues with timeout while using WordAI and SpinnerChief
 
 ### v1.6.2 - 2019-01-31 
 **Changes:** 
 * Add MP3 as a supported format for
* Outgoing links should have rel=noopener
* Fix issue with SpinnerChief not spinning content
 
 ### v1.6.1 - 2018-12-22 
 **Changes:** 
 * Add support for extracting elements from custom feed tags
* Fix issue with Save button missing in Miscellaneous tab settings
* Fix issue with WordAI authentication
* Add Run Now button
* Add option to allow all items to be imported from the feed
 
 ### v1.6.0 - 2018-11-22 
 **Changes:** 
 * Add support for SpinnerChief
* Import Posts enabled for plan 1 users
* Fixed issues with posts spun with WordAI
* Number of posts imported can now be specified
* Fixed conflict with Avada
 
 ### v1.5.7 - 2018-06-26 
 **Changes:** 
 * Fixed problem with the price show/hide option not working with the custom templates
* Add error handling and support for the full content option
* Fixed Custom templates not working when a child theme is used
 
 ### v1.5.6 - 2018-05-14 
 **Changes:** 
 * New option for the Feed To Post feature - Get the full content from the feed item
* Updated the WordAI integration with logging and correct replacement of [#content_wordai]
 
 ### v1.5.5 - 2018-04-02 
 **Changes:** 
 * Remove redundant gr text on style2 template.
* Adds item description to magic tags.
* Adds compatibility with eBay feeds.
 
 ### v1.5.4 - 2018-03-07 
 **Changes:** 
 * Automatically adds canonical URLs for imported posts.
* Integrates canonical URL with the most popular SEO plugins.
 
 ### v1.5.3 - 2018-02-20 
 **Changes:** 
 * Improves Feed To Post feature.
 
 ### v1.5.2 - 2018-01-10 
 **Changes:** 
 * Fix older imports default status.
  
 ### v1.5.1 - 2018-01-05 
 **Changes:** 
 * Adds post status selector for importing schedule. 
* Adds hook after importing action.
* Adds full content import, if exists.
 
 ### v1.5.0 - 2017-11-03 
 **Changes:** 
 * Improvements to Feed to Post mechanism. 
* Changes to shop templates.
 
 ### v1.4.1 - 2017-08-17 
 **Changes:** 
 * Fixed assets loading.
* Improved features loading.
 
 ### v1.4.0 - 2017-08-17 
 **Changes:** 
 * Added content aware templates ( render audio markup for audio RSS feeds ) 
* Added integration with WordAI
* Fixed feed categories limit bug.
 
 ### v1.3.1 - 2017-07-17 
 **Changes:** 
 * FIX: ( Fixed links not displaying correctly if imported in content )
 
 ### v1.3.0 - 2017-06-21 
 **Changes:** 
 * Fixed category map for imported posts.
* Added item_link magic tag.
* Added next import ETA.
 
 ### v1.2.4 - 2017-05-31 
 **Changes:** 
 - Fixed notices in admin notifications.
- Added composer lock to repo.
 
 ### v1.2.3 - 2017-05-30 
 **Changes:** 
  
 ### v1.2.2 - 2017-05-29 
 **Changes:** 
  
 ### v1.2.1 - 2017-05-18 
 **Changes:** 
 - Fixed license filter.
 
 ### v1.2.0 - 2017-05-17 
 **Changes:** 
 - Added feed to post feature.
- Improved CI process.
 

### 1.1.2 - 03/02/2017

**Changes:** 

- Fixed fatal error when lite is not installed.



### 1.1.1 - 11/01/2017

**Changes:** 

- Fixed free file inclusion


### 1.1.0 - 10/01/2017

**Changes:** 

- Added tgm for free plugin

- Added keywords blacklist option


### 1.0.1 - 06/01/2017

**Changes:** 

- Added links for price label

- Changed textdomain to match the lite


### 1.0.0 - 03/01/2017

**Changes:** 

- Release 1.0.0
