struct VSOut { @builtin(position) pos: vec4<f32>; @location(0) uv: vec2<f32>; };
 @group(0) @binding(0) var samp: sampler;
 @group(0) @binding(1) var tex: texture_2d<f32>;
 @group(0) @binding(2) var<uniform> params: vec4<f32>; // brightness, contrast, saturation, pad

 @fragment
fn fs_main(in: VSOut) -> @location(0) vec4<f32> {
  var c = textureSample(tex, samp, in.uv);
  c.rgb = (c.rgb - vec3(0.5)) * params.y + vec3(0.5); // contrast
  c.rgb = c.rgb + params.x; // brightness
  let g = dot(c.rgb, vec3(0.299, 0.587, 0.114));
  c.rgb = mix(vec3(g), c.rgb, params.z); // saturation
  return c;
}