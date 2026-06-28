// Entry point for splent_feature_post frontend assets.
// Add your JavaScript here. Webpack compiles this into assets/dist/splent_feature_post.bundle.js
//
// To load the compiled bundle in the product layout, register it in hooks.py:
//
//   from splent_framework.hooks.template_hooks import register_template_hook
//   from flask import url_for
//
//   def post_scripts():
//       return '<script src="' + url_for("post.assets", subfolder="dist", filename="splent_feature_post.bundle.js") + '"></script>'
//
//   register_template_hook("layout.scripts", post_scripts)
