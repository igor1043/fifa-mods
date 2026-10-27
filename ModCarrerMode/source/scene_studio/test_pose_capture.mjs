import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {validateCapture,moveCapturePoint,layoutPeople} from './pose_capture.js';
const data=validateCapture(JSON.parse(await fs.readFile('./build/tests/ai-reference.json','utf8')));
assert.equal(data.people.length,11);assert.equal(data.people[0].keypoints3d.length,133);
assert.deepEqual(validateCapture(JSON.parse(JSON.stringify(data))),data);
for(const edit of [d=>d.schema=2,d=>d.people.push(d.people[0]),d=>d.people[0].keypoints3d[0][2]=NaN,d=>d.people[0].keypoints2d[0][2]=2,d=>d.people[0].keypoints3d.pop(),d=>d.people[0].meters_per_pixel=0]){const invalid=structuredClone(data);edit(invalid);assert.throws(()=>validateCapture(invalid));}
const before=data.people[0].keypoints3d[9].slice(),pixel=data.people[0].keypoints2d[9].slice(),person=data.people[0];moveCapturePoint(person,9,pixel[0]+10,pixel[1]-20);assert.ok(Math.abs(person.keypoints3d[9][0]-before[0]-10*person.meters_per_pixel)<1e-9);assert.ok(Math.abs(person.keypoints3d[9][1]-before[1]-20*person.meters_per_pixel)<1e-9);assert.equal(person.keypoints3d[9][2],before[2]);assert.equal(person.keypoints3d[9][3],1);
assert.ok(layoutPeople(data.people).flat().every(Number.isFinite));assert.deepEqual(layoutPeople([]),[]);
const configured=validateCapture({...data,retarget:{confidence:.45,depth:.7,mirror:true,fingers:false,ground:true},people:data.people.map(p=>({...p,suggestedPlayerId:227275}))});assert.deepEqual(validateCapture(JSON.parse(JSON.stringify(configured))),configured);assert.equal(configured.people[0].suggestedPlayerId,227275);assert.equal(configured.retarget.depth,.7);
console.log('PASS: real capture round trip, malformed maps, point corrections and multi-person layout');
