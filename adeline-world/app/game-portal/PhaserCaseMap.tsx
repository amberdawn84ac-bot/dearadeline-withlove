"use client";

import { useEffect, useRef } from "react";

type Direction = "up" | "down" | "left" | "right";

const locations = [
  { id: "bus", name: "Cleveland Avenue Bus", icon: "BUS", x: 115, y: 105, color: 0xb85f4c },
  { id: "newsroom", name: "Newsroom", icon: "NEWS", x: 585, y: 105, color: 0x426b91 },
  { id: "organizer", name: "Organizer’s Kitchen", icon: "KITCHEN", x: 120, y: 405, color: 0xa56b3d },
  { id: "courthouse", name: "Federal Courthouse", icon: "COURT", x: 580, y: 405, color: 0x536b55 },
];

export default function PhaserCaseMap({ onVisit, visited }: { onVisit: (id: string) => void; visited: string[] }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<{ destroy: (removeCanvas?: boolean) => void } | null>(null);
  const onVisitRef = useRef(onVisit);
  const visitedRef = useRef(visited);
  const controls = useRef<Record<Direction, boolean>>({ up: false, down: false, left: false, right: false });
  onVisitRef.current = onVisit;
  visitedRef.current = visited;

  useEffect(() => {
    if (!mountRef.current || gameRef.current) return;
    let alive = true;
    void import("phaser").then((module) => {
      if (!alive || !mountRef.current) return;
      const Phaser = module.default;
      class MontgomeryScene extends Phaser.Scene {
        player!: InstanceType<typeof Phaser.Physics.Arcade.Sprite>;
        cursors!: InstanceType<typeof Phaser.Types.Input.Keyboard.CursorKeys>;
        keys!: Record<string, InstanceType<typeof Phaser.Input.Keyboard.Key>>;
        lastStop = "";
        create() {
          this.cameras.main.setBackgroundColor("#cfc18d");
          const ground = this.add.graphics();
          ground.fillStyle(0xd7c993, 1).fillRect(0, 0, 700, 520);
          ground.lineStyle(2, 0xb6a873, .35);
          for (let x = 0; x < 700; x += 44) ground.lineBetween(x, 0, x, 520);
          for (let y = 0; y < 520; y += 44) ground.lineBetween(0, y, 700, y);
          ground.lineStyle(56, 0x94866b, 1).lineBetween(-40, 310, 740, 210);
          ground.lineStyle(4, 0xeadcae, 1).lineBetween(-40, 282, 740, 182).lineBetween(-40, 338, 740, 238);
          ground.lineStyle(54, 0x94866b, 1).lineBetween(330, -30, 390, 550);
          ground.lineStyle(4, 0xeadcae, 1).lineBetween(303, -30, 363, 550).lineBetween(357, -30, 417, 550);

          const avatarTexture = this.textures.createCanvas("adeline-detective", 44, 44)!;
          const ctx = avatarTexture.context;
          ctx.fillStyle = "#e3a84a"; ctx.beginPath(); ctx.arc(22, 22, 18, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = "#263d32"; ctx.beginPath(); ctx.arc(16, 19, 3, 0, Math.PI * 2); ctx.arc(28, 19, 3, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = "#263d32"; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(22, 25, 7, .2, Math.PI - .2); ctx.stroke(); avatarTexture.refresh();
          this.player = this.physics.add.sprite(350, 270, "adeline-detective").setCircle(18).setCollideWorldBounds(true).setDepth(5);

          const walls = this.physics.add.staticGroup();
          locations.forEach((place) => {
            const building = this.add.rectangle(place.x, place.y, 150, 84, place.color).setStrokeStyle(5, 0xf5e6bb);
            walls.add(building);
            this.add.text(place.x, place.y - 9, place.icon, { color: "#fff9df", fontFamily: "Nunito, sans-serif", fontSize: "13px", fontStyle: "bold" }).setOrigin(.5);
            this.add.text(place.x, place.y + 15, place.name, { color: "#ffffff", fontFamily: "Nunito, sans-serif", fontSize: "11px", fontStyle: "bold", align: "center", wordWrap: { width: 132 } }).setOrigin(.5);
            const zone = this.add.zone(place.x, place.y, 190, 125);
            this.physics.add.existing(zone, true);
            this.physics.add.overlap(this.player, zone, () => {
              if (this.lastStop === place.id) return;
              this.lastStop = place.id; onVisitRef.current(place.id);
              this.cameras.main.flash(170, 239, 194, 92, false);
            });
          });

          this.physics.add.collider(this.player, walls);
          this.cursors = this.input.keyboard!.createCursorKeys();
          this.keys = this.input.keyboard!.addKeys("W,A,S,D") as Record<string, InstanceType<typeof Phaser.Input.Keyboard.Key>>;
          this.add.text(350, 18, "Walk close to a location to open its record", { color: "#2a4236", backgroundColor: "#fff2c9", fontFamily: "Nunito, sans-serif", fontSize: "12px", fontStyle: "bold", padding: { x: 10, y: 6 } }).setOrigin(.5).setScrollFactor(0);
        }
        update() {
          const speed = 190; let x = 0, y = 0;
          if (this.cursors.left.isDown || this.keys.A.isDown || controls.current.left) x -= 1;
          if (this.cursors.right.isDown || this.keys.D.isDown || controls.current.right) x += 1;
          if (this.cursors.up.isDown || this.keys.W.isDown || controls.current.up) y -= 1;
          if (this.cursors.down.isDown || this.keys.S.isDown || controls.current.down) y += 1;
          const vector = new Phaser.Math.Vector2(x, y).normalize().scale(speed);
          this.player.setVelocity(vector.x, vector.y);
          if (!x && !y) this.lastStop = "";
        }
      }
      gameRef.current = new Phaser.Game({ type: Phaser.AUTO, width: 700, height: 520, parent: mountRef.current, backgroundColor: "#cfc18d", physics: { default: "arcade", arcade: { gravity: { x: 0, y: 0 }, debug: false } }, scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }, scene: MontgomeryScene, render: { antialias: true, pixelArt: false } });
    });
    return () => { alive = false; gameRef.current?.destroy(true); gameRef.current = null; };
  }, []);

  function press(direction: Direction, value: boolean) { controls.current[direction] = value; }
  return <div className="phaser-case-shell"><div ref={mountRef} className="phaser-case-canvas" aria-label="Playable map of Montgomery. Use arrow keys, WASD, or the on-screen direction controls." /><div className="phaser-dpad" aria-label="Move detective"><button onPointerDown={() => press("up", true)} onPointerUp={() => press("up", false)} onPointerLeave={() => press("up", false)}>↑</button><button onPointerDown={() => press("left", true)} onPointerUp={() => press("left", false)} onPointerLeave={() => press("left", false)}>←</button><button onPointerDown={() => press("down", true)} onPointerUp={() => press("down", false)} onPointerLeave={() => press("down", false)}>↓</button><button onPointerDown={() => press("right", true)} onPointerUp={() => press("right", false)} onPointerLeave={() => press("right", false)}>→</button></div><small>PHASER 3 · ARCADE PHYSICS</small></div>;
}
