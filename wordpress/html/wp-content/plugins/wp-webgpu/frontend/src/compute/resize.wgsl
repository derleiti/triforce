 @group(0) @binding(0) var<storage, read>  src: array<u32>;
 @group(0) @binding(1) var<storage, read_write> dst: array<u32>;
 @group(0) @binding(2) var<uniform> dims: vec4<u32>; // sw,sh,dw,dh

 @compute @workgroup_size(8,8)
fn main( @builtin(global_invocation_id) gid: vec3<u32>) {
  if (gid.x >= dims.z || gid.y >= dims.w) { return; }

  let src_width  = f32(dims.x);
  let src_height = f32(dims.y);
  let dst_width  = f32(dims.z);
  let dst_height = f32(dims.w);

  let x_ratio = src_width / dst_width;
  let y_ratio = src_height / dst_height;

  let px = f32(gid.x);
  let py = f32(gid.y);

  let x_src = px * x_ratio;
  let y_src = py * y_ratio;

  let x_floor = floor(x_src);
  let y_floor = floor(y_src);

  let x_ceil = min(x_floor + 1.0, src_width - 1.0);
  let y_ceil = min(y_floor + 1.0, src_height - 1.0);

  let x_weight = x_src - x_floor;
  let y_weight = y_src - y_floor;

  let c00_idx = u32(y_floor) * dims.x + u32(x_floor);
  let c10_idx = u32(y_floor) * dims.x + u32(x_ceil);
  let c01_idx = u32(y_ceil)  * dims.x + u32(x_floor);
  let c11_idx = u32(y_ceil)  * dims.x + u32(x_ceil);

  let c00 = unpack4x8unorm(src[c00_idx]);
  let c10 = unpack4x8unorm(src[c10_idx]);
  let c01 = unpack4x8unorm(src[c01_idx]);
  let c11 = unpack4x8unorm(src[c11_idx]);

  let c_top    = mix(c00, c10, x_weight);
  let c_bottom = mix(c01, c11, x_weight);
  let final_color = mix(c_top, c_bottom, y_weight);

  dst[gid.y * dims.z + gid.x] = pack4x8unorm(final_color);
}