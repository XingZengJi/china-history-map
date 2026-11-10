const fs=require('fs'),ts=require('topojson-server'),tsi=require('topojson-simplify'),tc=require('topojson-client');
const meta=JSON.parse(fs.readFileSync('build/geo/frames_meta.json'));
function simp(fc,minW,q){ // topology -> simplify -> quantize
  let t=ts.topology({o:fc},1e6);
  t=tsi.presimplify(t); t=tsi.simplify(t,minW); t=tsi.filter(t,tsi.filterWeight(t,minW*4));
  return tc.quantize(t,q);
}
const out={frames:[]};
meta.forEach((m,i)=>{
  const fc=JSON.parse(fs.readFileSync(`build/geo/frame_${i}.geojson`));
  out.frames.push({y0:m.y0,y1:m.y1,snap:m.snap,texts:m.texts,topo:simp(fc,0.0012,3e4)});
});
out.land=simp(JSON.parse(fs.readFileSync('build/geo/land.geojson')),0.0008,3e4);
out.rivers=simp(JSON.parse(fs.readFileSync('build/geo/rivers.geojson')),0.0006,3e4);
out.lakes=simp(JSON.parse(fs.readFileSync('build/geo/lakes.geojson')),0.001,3e4);
out.pol=JSON.parse(fs.readFileSync('scripts/polities.json'));
const js='window.ATLAS='+JSON.stringify(out)+';';
fs.writeFileSync('site/data.js',js);
console.log('data.js',(js.length/1024).toFixed(0),'KB; frames',out.frames.length);
out.frames.forEach((f,i)=>{const n=JSON.stringify(f.topo).length; if(n>60000) console.log(i,f.y0,n)});
console.log('land',JSON.stringify(out.land).length,'rivers',JSON.stringify(out.rivers).length);
